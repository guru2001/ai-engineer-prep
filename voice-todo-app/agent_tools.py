"""Agent tools for task management"""
import asyncio
import re
from typing import Optional
from datetime import datetime, timedelta
from langchain.tools import tool
from database import Database
from models import TaskCreate, TaskUpdate, Priority, Category
from dateutil import parser as date_parser
from logger_config import logger


def run_async(coro):
    """Helper to run async code from sync context, handling existing event loops"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to use a different approach
            # Create a new task in a thread-safe way
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create a new one
        return asyncio.run(coro)


def parse_relative_date(date_string: str) -> datetime:
    """Parse relative dates like 'today', 'tomorrow', 'next week', etc.
    
    Args:
        date_string: Natural language date string
        
    Returns:
        datetime object with the parsed date
        
    Raises:
        ValueError: If date cannot be parsed or string is not a valid date
    """
    if not date_string:
        raise ValueError("Date string cannot be empty")
    
    date_string_lower = date_string.lower().strip()
    now = datetime.now()
    
    # Reject strings that are clearly not dates (e.g., "time is wrong", "date is wrong")
    # These are complaints or statements, not date specifications
    non_date_phrases = [
        "time is", "date is", "time was", "date was", 
        "wrong time", "wrong date", "incorrect time", "incorrect date",
        "time wrong", "date wrong", "time incorrect", "date incorrect"
    ]
    if any(phrase in date_string_lower for phrase in non_date_phrases):
        raise ValueError(f"String '{date_string}' appears to be a statement about time/date, not a date specification")
    
    # Check if time is specified (e.g., "tomorrow at 3pm")
    # More specific patterns to avoid false positives
    has_time_spec = (
        " at " in date_string_lower or 
        re.search(r'\d{1,2}:\d{2}', date_string_lower) or  # HH:MM format
        re.search(r'\d{1,2}\s*(am|pm)', date_string_lower) or  # 3pm, 3 pm
        ("hour" in date_string_lower and any(word in date_string_lower for word in ["in", "at", "by"]))
    )
    
    # Handle relative dates
    if date_string_lower == "today" or date_string_lower.startswith("today "):
        if has_time_spec:
            # Parse with dateutil to get time component
            parsed = date_parser.parse(date_string, fuzzy=True, default=now)
            # Ensure it's today's date
            return parsed.replace(year=now.year, month=now.month, day=now.day)
        else:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    elif date_string_lower == "tomorrow" or date_string_lower.startswith("tomorrow "):
        tomorrow = now + timedelta(days=1)
        if has_time_spec:
            # Parse with dateutil to get time component, but use tomorrow's date
            parsed = date_parser.parse(date_string, fuzzy=True, default=tomorrow)
            return parsed.replace(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        else:
            return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    
    elif date_string_lower == "yesterday" or date_string_lower.startswith("yesterday "):
        yesterday = now - timedelta(days=1)
        if has_time_spec:
            parsed = date_parser.parse(date_string, fuzzy=True, default=yesterday)
            return parsed.replace(year=yesterday.year, month=yesterday.month, day=yesterday.day)
        else:
            return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    elif date_string_lower.startswith("next week"):
        days_ahead = 7 - now.weekday()  # Days until next Monday
        if days_ahead == 0:
            days_ahead = 7  # If today is Monday, go to next Monday
        next_week = now + timedelta(days=days_ahead)
        return next_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Handle "in X days/hours" patterns
    in_days_match = re.search(r'in\s+(\d+)\s+days?', date_string_lower)
    if in_days_match:
        days = int(in_days_match.group(1))
        future_date = now + timedelta(days=days)
        return future_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Try to parse with dateutil (handles absolute dates and more complex relative dates)
    # This handles cases like "tomorrow at 3pm", "next Monday", "December 25th", etc.
    # Use fuzzy=False for more strict parsing to avoid false positives
    try:
        # First try strict parsing
        parsed = date_parser.parse(date_string, fuzzy=False, default=now)
        # If the original string was a simple relative date without time, set to start of day
        if not has_time_spec and ("today" in date_string_lower or "tomorrow" in date_string_lower or 
                                    "yesterday" in date_string_lower or ("day" in date_string_lower and "in " in date_string_lower)):
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        return parsed
    except (ValueError, TypeError):
        # If strict parsing fails, try fuzzy but be more careful
        try:
            parsed = date_parser.parse(date_string, fuzzy=True, default=now)
            # Validate that we actually got a reasonable date (not too far in past/future)
            # If parsed date is more than 100 years away, it's probably wrong
            if abs((parsed - now).days) > 36500:
                raise ValueError(f"Parsed date '{parsed}' seems incorrect for input '{date_string}'")
            
            if not has_time_spec and ("today" in date_string_lower or "tomorrow" in date_string_lower or 
                                        "yesterday" in date_string_lower or ("day" in date_string_lower and "in " in date_string_lower)):
                parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
            return parsed
        except Exception as e:
            raise ValueError(f"Could not parse date '{date_string}': {str(e)}")


def create_agent_tools(db: Database, session_id: Optional[str] = None):
    """Create and return all agent tools
    
    Args:
        db: Database instance
        session_id: Session ID for user isolation (optional)
    """
    
    @tool
    def list_tasks(category: Optional[str] = None) -> str:
        """List all tasks. If category is provided, filter by category.
        
        Args:
            category: Optional category to filter by. Must be one of: 'work', 'personal', 'administrative', 'shopping'
        """
        try:
            tasks = db.get_all_tasks(category=category, session_id=session_id)
            if not tasks:
                return "No tasks found." + (f" (category: {category})" if category else "")
            
            result = f"Found {len(tasks)} task(s):\n"
            for i, task in enumerate(tasks, 1):
                result += f"{i}. [{task.id}] {task.title}"
                if task.category:
                    category_value = task.category.value if isinstance(task.category, Category) else task.category
                    result += f" (Category: {category_value})"
                if task.priority != Priority.MEDIUM:
                    result += f" [Priority: {task.priority.value.upper()}]"
                if task.scheduled_time:
                    result += f" (Scheduled: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')})"
                result += "\n"
            return result.strip()
        except Exception as e:
            logger.error(f"Error in list_tasks: {e}", exc_info=True)
            return f"Error listing tasks: {str(e)}"

    @tool
    def create_task(title: str, priority: str = "medium", scheduled_time: Optional[str] = None, category: Optional[str] = None) -> str:
        """Create a new task.
        
        Args:
            title: The task title (required, must be non-empty)
            priority: Priority level (low, medium, high) - defaults to medium
            scheduled_time: Optional scheduled time (ISO format or natural language like "tomorrow", "next week")
            category: Optional category for the task. Must be one of: 'work', 'personal', 'administrative', 'shopping'
        """
        try:
            # Input validation
            if not title or not title.strip():
                return "Error: Task title cannot be empty."
            
            title = title.strip()
            
            # Validate and map priority
            priority_map = {
                "low": Priority.LOW,
                "medium": Priority.MEDIUM,
                "high": Priority.HIGH
            }
            priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

            # Validate and map category
            category_enum = None
            if category:
                category_lower = category.strip().lower()
                category_map = {
                    "work": Category.WORK,
                    "personal": Category.PERSONAL,
                    "administrative": Category.ADMINISTRATIVE,
                    "admin": Category.ADMINISTRATIVE,  # Allow 'admin' as shorthand
                    "shopping": Category.SHOPPING,
                    "shop": Category.SHOPPING  # Allow 'shop' as shorthand
                }
                category_enum = category_map.get(category_lower)
                if category_enum is None:
                    return f"Error: Invalid category '{category}'. Must be one of: work, personal, administrative, shopping."

            # Parse scheduled time
            scheduled_dt = None
            if scheduled_time:
                try:
                    scheduled_dt = parse_relative_date(scheduled_time)
                    logger.debug(f"Parsed scheduled_time '{scheduled_time}' to {scheduled_dt}")
                except ValueError as e:
                    logger.warning(f"Failed to parse scheduled_time '{scheduled_time}': {e}")
                    return f"Error: Could not parse scheduled time '{scheduled_time}'. Please use formats like 'tomorrow', 'today', '2024-12-25', or 'next week'."

            task = TaskCreate(
                title=title,
                priority=priority_enum,
                scheduled_time=scheduled_dt,
                category=category_enum
            )
            # Run async database call in sync context
            created = run_async(db.create_task(task, session_id=session_id))
            logger.info(f"Created task: {created.id} - {created.title}")
            return f"Created task: '{created.title}' (ID: {created.id})"
        except ValueError as e:
            logger.error(f"Validation error in create_task: {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Error in create_task: {e}", exc_info=True)
            return f"Error creating task: {str(e)}"

    @tool
    def update_task(task_id: Optional[int] = None, task_title: Optional[str] = None,
                    new_title: Optional[str] = None, priority: Optional[str] = None,
                    scheduled_time: Optional[str] = None, category: Optional[str] = None) -> str:
        """Update a task. You can identify the task by ID or by searching for a title match.
        
        Args:
            task_id: The task ID (if known)
            task_title: Search for task by title (partial match)
            new_title: New title for the task
            priority: New priority (low, medium, high)
            scheduled_time: New scheduled time (ISO format or natural language)
            category: New category
        """
        try:
            # Find task if not ID provided
            if not task_id and task_title:
                tasks = run_async(db.search_tasks(task_title, session_id=session_id))
                if tasks:
                    task_id = tasks[0].id
                    logger.debug(f"Found task by title '{task_title}': ID {task_id}")
                else:
                    return f"Task with title containing '{task_title}' not found."

            if not task_id:
                return "Please specify a task ID or title to update."

            existing_task = db.get_task(task_id, session_id=session_id)
            if not existing_task:
                return f"Task ID {task_id} not found."

            # Build update data
            update_data = {}
            if new_title:
                if not new_title.strip():
                    return "Error: New title cannot be empty."
                update_data["title"] = new_title.strip()
            if priority:
                priority_map = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
                priority_enum = priority_map.get(priority.lower())
                if priority_enum is None:
                    return f"Error: Invalid priority '{priority}'. Use 'low', 'medium', or 'high'."
                update_data["priority"] = priority_enum
            if scheduled_time:
                try:
                    update_data["scheduled_time"] = parse_relative_date(scheduled_time)
                    logger.debug(f"Parsed scheduled_time '{scheduled_time}' to {update_data['scheduled_time']}")
                except ValueError as e:
                    logger.warning(f"Failed to parse scheduled_time '{scheduled_time}': {e}")
                    return f"Error: Could not parse scheduled time '{scheduled_time}'. Please use formats like 'tomorrow', 'today', '2024-12-25', or 'next week'."
            if category:
                category_lower = category.strip().lower()
                category_map = {
                    "work": Category.WORK,
                    "personal": Category.PERSONAL,
                    "administrative": Category.ADMINISTRATIVE,
                    "admin": Category.ADMINISTRATIVE,
                    "shopping": Category.SHOPPING,
                    "shop": Category.SHOPPING
                }
                category_enum = category_map.get(category_lower)
                if category_enum is None:
                    return f"Error: Invalid category '{category}'. Must be one of: work, personal, administrative, shopping."
                update_data["category"] = category_enum

            if not update_data:
                return "No update fields provided."

            task_update = TaskUpdate(**update_data)
            updated = run_async(db.update_task(task_id, task_update, session_id=session_id))

            if updated:
                logger.info(f"Updated task: {task_id}")
                return f"Updated task ID {task_id}: '{updated.title}'"
            else:
                return f"Task ID {task_id} not found."
        except ValueError as e:
            logger.error(f"Validation error in update_task: {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Error in update_task: {e}", exc_info=True)
            return f"Error updating task: {str(e)}"

    @tool
    def delete_task(task_id: Optional[int] = None, task_title: Optional[str] = None, task_number: Optional[int] = None) -> str:
        """Delete a task. You can identify it by ID, title search, or task number (which is the task ID).
        
        Args:
            task_id: The task ID (if known)
            task_title: Search for task by title (partial match like "compliances")
            task_number: The task ID (e.g., "delete task 3" means delete task with ID 3)
        """
        try:
            # If task_number is provided, treat it as task_id
            if task_number and not task_id:
                task_id = task_number
                logger.debug(f"Using task_number {task_number} as task_id")

            # Find task by title
            if not task_id and task_title:
                tasks = run_async(db.search_tasks(task_title, session_id=session_id))
                if tasks:
                    task_id = tasks[0].id
                    logger.debug(f"Found task by title '{task_title}': ID {task_id}")
                else:
                    return f"Task with title containing '{task_title}' not found."

            if not task_id:
                return "Please specify a task ID, title, or number to delete."

            # Verify task exists before deleting
            task = db.get_task(task_id, session_id=session_id)
            if not task:
                return f"Task ID {task_id} not found."

            db.delete_task(task_id, session_id=session_id)
            logger.info(f"Deleted task: {task_id} - {task.title}")
            return f"Deleted task: '{task.title}' (ID: {task_id})"
        except Exception as e:
            logger.error(f"Error in delete_task: {e}", exc_info=True)
            return f"Error deleting task: {str(e)}"

    @tool
    def search_tasks(query: str) -> str:
        """Search tasks by title or category using semantic search.
        
        Args:
            query: Search keyword or phrase (e.g., "meetings", "grocery shopping")
        """
        try:
            if not query or not query.strip():
                return "Error: Search query cannot be empty."
            
            tasks = run_async(db.search_tasks(query.strip(), session_id=session_id))
            if not tasks:
                return f"No tasks found matching '{query}'."
            
            result = f"Found {len(tasks)} task(s) matching '{query}':\n"
            for i, task in enumerate(tasks, 1):
                result += f"{i}. [{task.id}] {task.title}"
                if task.category:
                    category_value = task.category.value if isinstance(task.category, Category) else task.category
                    result += f" (Category: {category_value})"
                result += "\n"
            return result.strip()
        except Exception as e:
            logger.error(f"Error in search_tasks: {e}", exc_info=True)
            return f"Error searching tasks: {str(e)}"

    return [list_tasks, create_task, update_task, delete_task, search_tasks]

