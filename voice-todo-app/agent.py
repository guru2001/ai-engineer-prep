import os
from typing import Optional
from datetime import datetime
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.tools import tool
from database import Database
from models import TaskCreate, TaskUpdate, Priority
from dateutil import parser as date_parser


class TodoAgent:
    def __init__(self, db: Database, openai_api_key: Optional[str] = None):
        self.db = db
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )
        self.agent = self._create_agent()

    def _create_agent(self):
        """Create the LangChain agent with tools"""
        db = self.db

        # ------------------------ TOOLS ------------------------

        @tool
        def list_tasks(category: Optional[str] = None) -> str:
            """List all tasks. If category is provided, filter by category.
            
            Args:
                category: Optional category to filter by (e.g., 'administrative', 'work', 'personal')
            """
            tasks = db.get_all_tasks(category=category)
            if not tasks:
                return "No tasks found." + (f" (category: {category})" if category else "")
            
            result = f"Found {len(tasks)} task(s):\n"
            for i, task in enumerate(tasks, 1):
                result += f"{i}. [{task.id}] {task.title}"
                if task.category:
                    result += f" (Category: {task.category})"
                if task.priority != Priority.MEDIUM:
                    result += f" [Priority: {task.priority.value.upper()}]"
                if task.scheduled_time:
                    result += f" (Scheduled: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')})"
                result += "\n"
            return result.strip()

        @tool
        def create_task(title: str, priority: str = "medium", scheduled_time: Optional[str] = None, category: Optional[str] = None) -> str:
            """Create a new task.
            
            Args:
                title: The task title
                priority: Priority level (low, medium, high)
                scheduled_time: Optional scheduled time (ISO format or natural language)
                category: Optional category for the task
            """
            try:
                priority_map = {
                    "low": Priority.LOW,
                    "medium": Priority.MEDIUM,
                    "high": Priority.HIGH
                }
                priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

                scheduled_dt = None
                if scheduled_time:
                    try:
                        scheduled_dt = date_parser.parse(scheduled_time)
                    except:
                        pass

                task = TaskCreate(
                    title=title,
                    priority=priority_enum,
                    scheduled_time=scheduled_dt,
                    category=category
                )
                created = db.create_task(task)
                return f"Created task: '{created.title}' (ID: {created.id})"
            except Exception as e:
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
                if not task_id and task_title:
                    tasks = db.search_tasks(task_title)
                    if tasks:
                        task_id = tasks[0].id
                    else:
                        return f"Task with title containing '{task_title}' not found."

                if not task_id:
                    return "Please specify a task ID or title to update."

                update_data = {}
                if new_title:
                    update_data["title"] = new_title
                if priority:
                    priority_map = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
                    update_data["priority"] = priority_map.get(priority.lower(), Priority.MEDIUM)
                if scheduled_time:
                    try:
                        update_data["scheduled_time"] = date_parser.parse(scheduled_time)
                    except:
                        pass
                if category:
                    update_data["category"] = category

                if not update_data:
                    return "No update fields provided."

                task_update = TaskUpdate(**update_data)
                updated = db.update_task(task_id, task_update)

                if updated:
                    return f"Updated task ID {task_id}: '{updated.title}'"
                else:
                    return f"Task ID {task_id} not found."
            except Exception as e:
                return f"Error updating task: {str(e)}"

        @tool
        def delete_task(task_id: Optional[int] = None, task_title: Optional[str] = None, task_number: Optional[int] = None) -> str:
            """Delete a task. You can identify it by ID, title search, or position number.
            
            Args:
                task_id: The task ID (if known)
                task_title: Search for task by title (partial match like "compliances")
                task_number: The position number (e.g., "4th task" = 4)
            """
            try:
                if task_number:
                    tasks = db.get_all_tasks()
                    if 1 <= task_number <= len(tasks):
                        task_id = tasks[task_number - 1].id
                    else:
                        return f"Task number {task_number} not found."

                if not task_id and task_title:
                    tasks = db.search_tasks(task_title)
                    if tasks:
                        task_id = tasks[0].id
                    else:
                        return f"Task with title containing '{task_title}' not found."

                if not task_id:
                    return "Please specify a task ID, title, or number to delete."

                task = db.get_task(task_id)
                if not task:
                    return f"Task ID {task_id} not found."

                db.delete_task(task_id)
                return f"Deleted task: '{task.title}' (ID: {task_id})"
            except Exception as e:
                return f"Error deleting task: {str(e)}"

        @tool
        def search_tasks(query: str) -> str:
            """Search tasks by title or category.
            
            Args:
                query: Search keyword
            """
            tasks = db.search_tasks(query)
            if not tasks:
                return f"No tasks found matching '{query}'."
            
            result = f"Found {len(tasks)} task(s) matching '{query}':\n"
            for i, task in enumerate(tasks, 1):
                result += f"{i}. [{task.id}] {task.title}"
                if task.category:
                    result += f" (Category: {task.category})"
                result += "\n"
            return result.strip()

        tools = [list_tasks, create_task, update_task, delete_task, search_tasks]

        # ---------------------- SYSTEM PROMPT -------------------------

        system_prompt = """You are a helpful assistant for managing a to-do list.
You can help users create, read, update, and delete tasks.

When users ask to:
- "Show me all [category] tasks" or "List [category] tasks" → use list_tasks
- "Create a task to do X" or "Make me a task for Y" → use create_task
- "Update task X" or "Change task Y" or "Push task Z to tomorrow" → use update_task
- "Delete task X" or "Remove task Y" → use delete_task
- "Find tasks about X" → use search_tasks

For priorities, interpret: "high", "important", "urgent" → HIGH
"low", "not important" → LOW
"medium", "normal" → MEDIUM

For scheduled times, parse natural language like "tomorrow", "next week", "in 2 days", etc.
Always be helpful and confirm actions clearly."""

        # ---------------------- AGENT --------------------------

        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )

    # ---------------------- PUBLIC API ------------------------

    def process_command(self, command: str) -> str:
        try:
            # In LangChain 1.0.5, the agent expects messages format
            result = self.agent.invoke({"messages": [HumanMessage(content=command)]})
            # Extract the response from the result
            # The result is a dict with "messages" key containing a list of messages
            # The last message should be an AIMessage with the final response
            if "messages" in result and result["messages"]:
                # Find the last AIMessage (skip ToolMessages)
                for message in reversed(result["messages"]):
                    if isinstance(message, AIMessage) and message.content:
                        return message.content
                # Fallback: get the last message
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    return last_message.content or "No response generated."
                elif isinstance(last_message, dict) and "content" in last_message:
                    return last_message["content"] or "No response generated."
            return "No response generated."
        except Exception as e:
            import traceback
            error_msg = f"Error processing command: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return error_msg
