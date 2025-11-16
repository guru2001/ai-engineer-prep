import sqlite3
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager
from models import Task, TaskCreate, TaskUpdate, Priority


class Database:
    def __init__(self, db_path: str = "todos.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with tasks table"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    scheduled_time TEXT,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    category TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_task(self, task: TaskCreate) -> Task:
        """Create a new task"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO tasks (title, scheduled_time, priority, category, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task.title,
                task.scheduled_time.isoformat() if task.scheduled_time else None,
                task.priority.value,
                task.category,
                datetime.now().isoformat()
            ))
            conn.commit()
            task_id = cursor.lastrowid
            return self.get_task(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row:
                return self._row_to_task(row)
            return None

    def get_all_tasks(self, category: Optional[str] = None) -> List[Task]:
        """Get all tasks, optionally filtered by category"""
        with self._get_connection() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE category = ? ORDER BY created_at DESC",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC"
                ).fetchall()
            return [self._row_to_task(row) for row in rows]

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """Update a task"""
        with self._get_connection() as conn:
            updates = []
            values = []
            
            if task_update.title is not None:
                updates.append("title = ?")
                values.append(task_update.title)
            if task_update.scheduled_time is not None:
                updates.append("scheduled_time = ?")
                values.append(task_update.scheduled_time.isoformat())
            if task_update.priority is not None:
                updates.append("priority = ?")
                values.append(task_update.priority.value)
            if task_update.category is not None:
                updates.append("category = ?")
                values.append(task_update.category)
            
            if not updates:
                return self.get_task(task_id)
            
            values.append(task_id)
            conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()
            return self.get_task(task_id)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search_tasks(self, query: str) -> List[Task]:
        """Search tasks by title or category"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE title LIKE ? OR category LIKE ? ORDER BY created_at DESC",
                (f"%{query}%", f"%{query}%")
            ).fetchall()
            return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a database row to a Task model"""
        scheduled_time = None
        if row["scheduled_time"]:
            scheduled_time = datetime.fromisoformat(row["scheduled_time"])
        
        return Task(
            id=row["id"],
            title=row["title"],
            scheduled_time=scheduled_time,
            priority=Priority(row["priority"]),
            category=row["category"],
            created_at=datetime.fromisoformat(row["created_at"])
        )

