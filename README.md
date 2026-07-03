# Preparing For AI Engineering

A collection of AI/LLM projects I've built while going deep on agent orchestration,
retrieval, and full-stack LLM apps.

## Projects

- **[doclens](./doclens)** — Chat with your PDFs: upload a document and get answers grounded in it with inline **page-level citations**. Built full-stack — React + FastAPI, Google Gemini for direct PDF understanding + structured citations, single-container Docker deploy.

- **[travel-agent](./travel-agent)** — *TravelBuddy*, a conversational trip planner that gathers your dates, budget, and interests and returns a tailored itinerary — auto-extracting mentioned cities and rendering map links. Built as a **LangGraph** agent with a Chainlit chat UI (OpenAI).

- **[voice-todo-app](./voice-todo-app)** — A voice-first to-do app: speak natural-language commands to create, update, delete, and find tasks, with spoken feedback. Built full-stack — FastAPI + a **LangChain** agent, Deepgram speech-to-text, and ChromaDB for semantic task search.

- **[langgraph-codes](./langgraph-codes)** — A reference collection of **LangGraph** patterns: threaded chat with in-memory and PostgreSQL checkpointing, token streaming, web search, and tool-calling (todo, calculator) — built while learning stateful agent orchestration.
