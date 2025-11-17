import os
from typing import Optional, List, Dict, Any
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from database import Database
from agent_tools import create_agent_tools
from logger_config import logger


class TodoAgent:
    def __init__(self, db: Database, openai_api_key: Optional[str] = None, 
                 model: str = "gpt-4o-mini", temperature: float = 0.0):
        """Initialize the TodoAgent
        
        Args:
            db: Database instance
            openai_api_key: OpenAI API key (optional, falls back to env var)
            model: OpenAI model to use
            temperature: Model temperature
        """
        self.db = db
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
        # Store chat history per session (session_id -> list of messages)
        self.chat_history: Dict[str, List[BaseMessage]] = {}
        # Store agents per session (session_id -> agent)
        self.agents: Dict[str, Any] = {}
        logger.info("TodoAgent initialized successfully")

    def _create_agent(self, session_id: Optional[str] = None):
        """Create the LangChain agent with tools
            
            Args:
            session_id: Session ID for user isolation (optional)
        """
        # Create tools
        tools = create_agent_tools(self.db, session_id=session_id)
        logger.debug(f"Created {len(tools)} agent tools")

        # Enhanced system prompt
        system_prompt = """You are a helpful and intelligent assistant for managing a to-do list.
            You help users create, read, update, and delete tasks using natural language commands.

            **Available Actions:**
            - List tasks: "Show me all tasks", "List work tasks", "What tasks do I have?"
            - Create tasks: "Create a task to buy groceries", "Add a high priority task for fixing bugs"
            - Update tasks: "Update task 1", "Change the grocery task to tomorrow", "Set task about meetings to high priority"
            - Delete tasks: "Delete task 3", "Remove the grocery task", "Delete the 4th task"
            - Search tasks: "Find tasks about meetings", "Search for grocery tasks"

            **Category System (4 predefined categories):**
            Tasks can be assigned to one of these categories:
            - WORK: Work-related tasks (e.g., "meetings", "projects", "deadlines", "code", "bugs", "reports")
            - PERSONAL: Personal tasks (e.g., "exercise", "hobbies", "family", "health", "self-care")
            - ADMINISTRATIVE: Administrative tasks (e.g., "taxes", "bills", "paperwork", "appointments", "compliance")
            - SHOPPING: Shopping tasks (e.g., "groceries", "buy", "purchase", "shopping list", "store")
            
            When creating or updating tasks, automatically assign the most appropriate category based on the task content.
            If the user explicitly mentions a category, use that. Otherwise, infer from the task title.

            **Priority Interpretation:**
            - HIGH: "high", "important", "urgent", "critical", "top priority"
            - MEDIUM: "medium", "normal", "regular" (default)
            - LOW: "low", "not important", "whenever", "optional"

            **Time Parsing:**
            Parse natural language dates like:
            - "tomorrow", "today", "next week", "in 2 days"
            - "December 25th", "2024-12-25", "next Monday"
            - Relative times: "in 3 hours", "next month"

            **Best Practices:**
            1. Always confirm actions clearly (e.g., "Created task: 'Buy groceries' (ID: 5)")
            2. If a task isn't found, suggest using list_tasks to see available tasks
            3. When updating, be specific about what changed
            4. For ambiguous requests, ask for clarification or use search_tasks first
            5. Be concise but informative in responses

            Always be helpful, accurate, and confirm what actions you've taken."""

        # Create agent
        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
        logger.info("LangChain agent created successfully")
        return agent

    # ---------------------- PUBLIC API ------------------------

    def process_command(self, command: str, session_id: str = "default", 
                       chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process a natural language command and return a response
        
        Args:
            command: The user's command as a string
            session_id: Session ID for maintaining chat history (default: "default")
            chat_history: Optional list of previous messages in format [{"role": "user", "content": "..."}, ...]
            
        Returns:
            Response string from the agent
        """
        if not command or not command.strip():
            logger.warning("Empty command received")
            return "Please provide a command. For example: 'Create a task to buy groceries'"
        
        command = command.strip()
        logger.info(f"Processing command: {command} (session: {session_id})")
        
        try:
            # Get or create agent for this session
            if session_id not in self.agents:
                self.agents[session_id] = self._create_agent(session_id=session_id)
            agent = self.agents[session_id]
            
            # Build message list with chat history
            messages: List[BaseMessage] = []
            
            # Add chat history if provided
            if chat_history:
                for msg in chat_history:
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant" or role == "ai":
                        messages.append(AIMessage(content=content))
            
            # Add current command
            messages.append(HumanMessage(content=command))
            
            # Invoke agent with messages (including history)
            result = agent.invoke({"messages": messages})
            
            # Extract the response from the result
            response = None
            if "messages" in result and result["messages"]:
                # Find the last AIMessage (skip ToolMessages)
                for message in reversed(result["messages"]):
                    if isinstance(message, AIMessage) and message.content:
                        response = message.content
                        logger.info(f"Agent response: {response[:100]}...")
                        break
                
                # Fallback: get the last message
            if not response:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    response = last_message.content or "No response generated."
                    logger.warning("Using fallback response extraction")
                elif isinstance(last_message, dict) and "content" in last_message:
                    response = last_message["content"] or "No response generated."
                    logger.warning("Using fallback response extraction (dict)")
            
            if not response:
                logger.error("No response found in agent result")
                return "No response generated. Please try rephrasing your command."
            
            # Store in chat history
            if session_id not in self.chat_history:
                self.chat_history[session_id] = []
            
            # Add user message and assistant response to history
            self.chat_history[session_id].append(HumanMessage(content=command))
            self.chat_history[session_id].append(AIMessage(content=response))
            
            # Limit history to last 20 messages (10 exchanges) to avoid token limits
            if len(self.chat_history[session_id]) > 20:
                self.chat_history[session_id] = self.chat_history[session_id][-20:]
            
            return response
            
        except ValueError as e:
            logger.error(f"Validation error processing command: {e}", exc_info=True)
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            return f"I encountered an error processing your command. Please try again or rephrasing your request."
    
    def get_chat_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """Get chat history for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of messages in format [{"role": "user", "content": "..."}, ...]
        """
        if session_id not in self.chat_history:
            return []
        
        history = []
        for msg in self.chat_history[session_id]:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def clear_chat_history(self, session_id: str = "default"):
        """Clear chat history for a session
        
        Args:
            session_id: Session ID
        """
        if session_id in self.chat_history:
            del self.chat_history[session_id]
            logger.info(f"Cleared chat history for session: {session_id}")
