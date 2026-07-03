# DocLens — Chat with your PDFs

Upload a PDF and ask questions about it. Answers come back **grounded in the
document with inline citations** to the exact page. The backend extracts the
PDF's text page by page and uses **OpenAI structured outputs** to return a typed
answer + citations (no vector database, no hallucinated sources).

**Stack:** FastAPI · SQLModel · OpenAI · pypdf · React + Vite · Docker.
The backend serves the built React app, so the whole thing runs as **one service**.

---

## Features

- 📄 Upload PDFs (stored in the database — no dependency on disk, so it survives restarts on any host)
- 💬 Ask questions; get answers with **page-level citations** and the exact quoted passage
- 🗂️ Multiple documents, each with its own persisted chat history
- 🔌 Model is one env var away from swapping (`gpt-4.1-nano` by default — cheapest; `gpt-4o-mini`, `gpt-4.1-mini` etc.)

## Architecture

```
React (Vite) ── /api ──► FastAPI ──► pypdf (per-page text) ──► OpenAI (structured citations)
                            │
                            └──► Postgres / SQLite  (documents + messages)
```

The API lives under `/api/*`; everything else serves the built React SPA.

---

## Run locally

**1. Backend** (`backend/`)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (`frontend/`) — in another terminal, for hot-reload dev:

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxies /api to :8000)
```

Get an API key at <https://platform.openai.com/api-keys>.

## Run as one container

```bash
docker build -t doclens .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... doclens
# open http://localhost:8000
```

Defaults to SQLite. For persistence across restarts, pass a Postgres URL:
`-e DATABASE_URL=postgresql://...`

---

## Deploy free (Render + Neon)

1. **Database** — create a free Postgres at [neon.tech](https://neon.tech); copy the connection string.
2. **Push** this repo to GitHub.
3. **Render** → *New +* → *Blueprint* → pick the repo (it reads `render.yaml`).
4. Set the two secrets in the Render dashboard:
   - `OPENAI_API_KEY` = your OpenAI key
   - `DATABASE_URL` = your Neon connection string
5. Deploy. Your live URL is `https://doclens.onrender.com` (free tier sleeps after ~15 min idle → first request has a cold start).

> The frontend is served by the backend, so there's **nothing separate to deploy** — one URL for the whole app.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). |
| `OPENAI_MODEL` | `gpt-4.1-nano` | `gpt-4o-mini` / `gpt-4.1-mini` for higher quality. |
| `DATABASE_URL` | `sqlite:///./doclens.db` | Use a Postgres URL in production. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated; only matters if you host the frontend separately. |
| `MAX_UPLOAD_MB` | `25` | Upload size cap. |
