import os
from typing import Optional
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
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
        self.agent = self._create_agent()
        logger.info("TodoAgent initialized successfully")

    def _create_agent(self):
        """Create the LangChain agent with tools"""
        # Create tools
        tools = create_agent_tools(self.db)
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

    def process_command(self, command: str) -> str:
        """Process a natural language command and return a response
        
        Args:
            command: The user's command as a string
            
        Returns:
            Response string from the agent
        """
        if not command or not command.strip():
            logger.warning("Empty command received")
            return "Please provide a command. For example: 'Create a task to buy groceries'"
        
        command = command.strip()
        logger.info(f"Processing command: {command}")
        
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
                        response = message.content
                        logger.info(f"Agent response: {response[:100]}...")
                        return response
                
                # Fallback: get the last message
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    response = last_message.content or "No response generated."
                    logger.warning("Using fallback response extraction")
                    return response
                elif isinstance(last_message, dict) and "content" in last_message:
                    response = last_message["content"] or "No response generated."
                    logger.warning("Using fallback response extraction (dict)")
                    return response
            
            logger.error("No response found in agent result")
            return "No response generated. Please try rephrasing your command."
            
        except ValueError as e:
            logger.error(f"Validation error processing command: {e}", exc_info=True)
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            # Don't expose full traceback to user, but log it
            return f"I encountered an error processing your command. Please try again or rephrasing your request."
