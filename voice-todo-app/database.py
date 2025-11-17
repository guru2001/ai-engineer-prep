import os
import chromadb
from datetime import datetime
from typing import List, Optional
from models import Task, TaskCreate, TaskUpdate, Priority
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
            parts.append(task.category)
        return " ".join(parts)

    def _task_to_metadata(self, task_id: int, task: TaskCreate, created_at: datetime) -> dict:
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
            metadata["category"] = task.category
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
            category=metadata.get("category"),
            created_at=datetime.fromisoformat(metadata["created_at"])
        )

    def create_task(self, task: TaskCreate) -> Task:
        """Create a new task"""
        task_id = self._get_next_id()
        created_at = datetime.now()
        
        # Generate text and embedding
        text = self._task_to_text(task)
        embedding = self._generate_embedding(text)
        
        # Prepare metadata
        metadata = self._task_to_metadata(task_id, task, created_at)
        
        # Add to ChromaDB
        self.collection.add(
            ids=[str(task_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID"""
        try:
            results = self.collection.get(ids=[str(task_id)])
            if results["ids"]:
                metadata = results["metadatas"][0]
                return self._metadata_to_task(metadata)
            return None
        except Exception:
            return None

    def get_all_tasks(self, category: Optional[str] = None) -> List[Task]:
        """Get all tasks, optionally filtered by category"""
        try:
            if category:
                # Filter by category in metadata
                results = self.collection.get(
                    where={"category": category}
                )
            else:
                # Get all tasks
                results = self.collection.get()
            
            tasks = []
            if results["ids"]:
                for metadata in results["metadatas"]:
                    tasks.append(self._metadata_to_task(metadata))
            
            # Sort by created_at descending
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}", exc_info=True)
            return []

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """Update a task"""
        existing_task = self.get_task(task_id)
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
        
        # Prepare updated metadata
        updated_metadata = {
            "id": str(task_id),
            "title": updated_title,
            "priority": updated_priority.value,
            "created_at": existing_task.created_at.isoformat(),
        }
        if updated_scheduled_time:
            updated_metadata["scheduled_time"] = updated_scheduled_time.isoformat()
        if updated_category:
            updated_metadata["category"] = updated_category
        
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
        
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        try:
            self.collection.delete(ids=[str(task_id)])
            return True
        except Exception:
            return False

    def search_tasks(self, query: str) -> List[Task]:
        """Search tasks using semantic search"""
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            
            # Perform semantic search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=10  # Return top 10 matches
            )
            
            tasks = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for metadata in results["metadatas"][0]:
                    tasks.append(self._metadata_to_task(metadata))
            
            # Sort by created_at descending
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks
        except Exception as e:
            logger.error(f"Error searching tasks: {e}", exc_info=True)
            return []
