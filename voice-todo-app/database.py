import os
import chromadb
from datetime import datetime
from typing import List, Optional
from models import Task, TaskCreate, TaskUpdate, Priority, Category
from openai import OpenAI
from logger_config import logger


class Database:
    def __init__(self, db_path: str = "./chroma_db", openai_api_key: Optional[str] = None):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="tasks",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        
        # Track next ID (ChromaDB doesn't auto-increment)
        self._init_id_counter()

    def _init_id_counter(self):
        """Initialize the ID counter based on existing tasks"""
        try:
            all_results = self.collection.get()
            if all_results["ids"]:
                # Find the maximum ID (handle both string and int IDs)
                max_id = 0
                for id_str in all_results["ids"]:
                    try:
                        id_int = int(id_str)
                        max_id = max(max_id, id_int)
                    except (ValueError, TypeError):
                        continue
                self._next_id = max_id + 1 if max_id > 0 else 1
            else:
                self._next_id = 1
        except Exception:
            self._next_id = 1

    def _get_next_id(self) -> int:
        """Get the next available task ID"""
        current_id = self._next_id
        self._next_id += 1
        return current_id
    
    def _parse_category(self, category_value: Optional[str]) -> Optional[Category]:
        """Parse category string to Category enum, with backward compatibility"""
        if not category_value:
            return None
        try:
            # Try to match by value
            for cat in Category:
                if cat.value.lower() == str(category_value).lower():
                    return cat
            # Backward compatibility: if it's a valid category string, convert it
            category_lower = str(category_value).lower()
            if category_lower in ["work", "personal", "administrative", "shopping"]:
                return Category(category_lower)
            return None
        except (ValueError, AttributeError):
            return None

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            # Fallback: return empty embedding if API fails
            logger.warning(f"Failed to generate embedding: {e}")
            return [0.0] * 1536  # Default dimension for text-embedding-3-small

    def _task_to_text(self, task: TaskCreate) -> str:
        """Convert task to text for embedding"""
        parts = [task.title]
        if task.category:
            # Handle Category enum or string
            category_value = task.category.value if isinstance(task.category, Category) else task.category
            parts.append(category_value)
        return " ".join(parts)

    def _task_to_metadata(self, task_id: int, task: TaskCreate, created_at: datetime, session_id: Optional[str] = None) -> dict:
        """Convert task to metadata dict for ChromaDB"""
        metadata = {
            "id": str(task_id),
            "title": task.title,
            "priority": task.priority.value,
            "created_at": created_at.isoformat(),
        }
        if task.scheduled_time:
            metadata["scheduled_time"] = task.scheduled_time.isoformat()
        if task.category:
            metadata["category"] = task.category.value if isinstance(task.category, Category) else task.category
        if session_id:
            metadata["session_id"] = session_id
        return metadata

    def _metadata_to_task(self, metadata: dict) -> Task:
        """Convert metadata dict to Task model"""
        scheduled_time = None
        if metadata.get("scheduled_time"):
            scheduled_time = datetime.fromisoformat(metadata["scheduled_time"])
        
        return Task(
            id=int(metadata["id"]),
            title=metadata["title"],
            scheduled_time=scheduled_time,
            priority=Priority(metadata["priority"]),
            category=self._parse_category(metadata.get("category")),
            created_at=datetime.fromisoformat(metadata["created_at"])
        )

    def create_task(self, task: TaskCreate, session_id: Optional[str] = None) -> Task:
        """Create a new task
        
        Args:
            task: Task data to create
            session_id: Session ID for user isolation (optional for backward compatibility)
        """
        task_id = self._get_next_id()
        created_at = datetime.now()
        
        # Generate text and embedding
        text = self._task_to_text(task)
        embedding = self._generate_embedding(text)
        
        # Prepare metadata
        metadata = self._task_to_metadata(task_id, task, created_at, session_id)
        
        # Add to ChromaDB
        self.collection.add(
            ids=[str(task_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        return self.get_task(task_id, session_id)

    def get_task(self, task_id: int, session_id: Optional[str] = None) -> Optional[Task]:
        """Get a task by ID
        
        Args:
            task_id: Task ID to retrieve
            session_id: Session ID to verify ownership (optional for backward compatibility)
        """
        try:
            results = self.collection.get(ids=[str(task_id)])
            if results["ids"]:
                metadata = results["metadatas"][0]
                # Verify session_id ownership if provided
                if session_id and metadata.get("session_id") and metadata.get("session_id") != session_id:
                    logger.warning(f"Task {task_id} does not belong to session {session_id}")
                    return None
                return self._metadata_to_task(metadata)
            return None
        except Exception:
            return None

    def get_all_tasks(self, category: Optional[str] = None, session_id: Optional[str] = None) -> List[Task]:
        """Get all tasks, optionally filtered by category and session_id
        
        Args:
            category: Optional category filter
            session_id: Session ID to filter tasks (optional for backward compatibility)
        """
        try:
            # Build where clause for filtering
            where_clause = {}
            if session_id:
                where_clause["session_id"] = session_id
            if category:
                where_clause["category"] = category
            
            if where_clause:
                results = self.collection.get(where=where_clause)
            else:
                # Get all tasks (backward compatibility - no filters)
                results = self.collection.get()
            
            tasks = []
            if results["ids"]:
                for metadata in results["metadatas"]:
                    # Additional filter for session_id if provided (for backward compatibility)
                    if session_id and metadata.get("session_id") and metadata.get("session_id") != session_id:
                        continue
                    tasks.append(self._metadata_to_task(metadata))
            
            # Sort by created_at descending
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}", exc_info=True)
            return []

    def update_task(self, task_id: int, task_update: TaskUpdate, session_id: Optional[str] = None) -> Optional[Task]:
        """Update a task
        
        Args:
            task_id: Task ID to update
            task_update: Task update data
            session_id: Session ID to verify ownership (optional for backward compatibility)
        """
        existing_task = self.get_task(task_id, session_id)
        if not existing_task:
            return None
        
        # Build updated task data
        updated_title = task_update.title if task_update.title is not None else existing_task.title
        updated_category = task_update.category if task_update.category is not None else existing_task.category
        updated_priority = task_update.priority if task_update.priority is not None else existing_task.priority
        updated_scheduled_time = task_update.scheduled_time if task_update.scheduled_time is not None else existing_task.scheduled_time
        
        # Check if we need to regenerate embedding (title or category changed)
        needs_embedding_update = (
            task_update.title is not None or 
            task_update.category is not None
        )
        
        # Create updated task for embedding generation
        updated_task_create = TaskCreate(
            title=updated_title,
            category=updated_category,
            priority=updated_priority,
            scheduled_time=updated_scheduled_time
        )
        
        # Prepare updated metadata (preserve session_id from existing task)
        updated_metadata = {
            "id": str(task_id),
            "title": updated_title,
            "priority": updated_priority.value,
            "created_at": existing_task.created_at.isoformat(),
        }
        if updated_scheduled_time:
            updated_metadata["scheduled_time"] = updated_scheduled_time.isoformat()
        if updated_category:
            # Handle Category enum or string
            if isinstance(updated_category, Category):
                updated_metadata["category"] = updated_category.value
            else:
                updated_metadata["category"] = updated_category
        # Preserve session_id from existing task metadata
        existing_results = self.collection.get(ids=[str(task_id)])
        if existing_results["ids"] and existing_results["metadatas"]:
            existing_metadata = existing_results["metadatas"][0]
            if existing_metadata.get("session_id"):
                updated_metadata["session_id"] = existing_metadata["session_id"]
        
        # Update in ChromaDB (delete and re-add since ChromaDB doesn't support partial updates well)
        # Get existing embedding if we don't need to regenerate
        if not needs_embedding_update:
            # Get existing data before deleting
            existing_results = self.collection.get(ids=[str(task_id)])
            if existing_results["ids"] and existing_results["embeddings"]:
                existing_embedding = existing_results["embeddings"][0]
                existing_text = existing_results["documents"][0]
            else:
                existing_embedding = None
                existing_text = None
        else:
            existing_embedding = None
            existing_text = None
        
        # Delete existing
        self.collection.delete(ids=[str(task_id)])
        
        # Prepare text and embedding
        if needs_embedding_update:
            text = self._task_to_text(updated_task_create)
            embedding = self._generate_embedding(text)
        else:
            # Use existing text and embedding
            text = existing_text or self._task_to_text(updated_task_create)
            embedding = existing_embedding or self._generate_embedding(text)
        
        # Re-add with updated data
        self.collection.add(
            ids=[str(task_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[updated_metadata]
        )
        
        return self.get_task(task_id, session_id)

    def delete_task(self, task_id: int, session_id: Optional[str] = None) -> bool:
        """Delete a task
        
        Args:
            task_id: Task ID to delete
            session_id: Session ID to verify ownership (optional for backward compatibility)
        """
        try:
            # Verify ownership if session_id provided
            if session_id:
                existing_task = self.get_task(task_id, session_id)
                if not existing_task:
                    logger.warning(f"Task {task_id} not found or doesn't belong to session {session_id}")
                    return False
            self.collection.delete(ids=[str(task_id)])
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}", exc_info=True)
            return False

    def search_tasks(self, query: str, session_id: Optional[str] = None) -> List[Task]:
        """Search tasks using semantic search
        
        Args:
            query: Search query string
            session_id: Session ID to filter tasks (optional for backward compatibility)
        """
        try:
            if not query or not query.strip():
                return []
            
            query = query.strip()
            
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            
            # Build where clause for filtering by session_id
            where_clause = None
            if session_id:
                where_clause = {"session_id": session_id}
            
            # Perform semantic search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=10,  # Return top 10 matches
                where=where_clause if where_clause else None
            )
            
            tasks = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for metadata in results["metadatas"][0]:
                    # Additional filter for session_id if provided (for backward compatibility)
                    if session_id and metadata.get("session_id") and metadata.get("session_id") != session_id:
                        continue
                    tasks.append(self._metadata_to_task(metadata))
            
            # Sort by created_at descending
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks
        except Exception as e:
            logger.error(f"Error searching tasks: {e}", exc_info=True)
            return []
