# Cairn

> Save articles with one click. Ask AI questions about what you've read.

Cairn is an AI-powered personal knowledge base built as a Chrome Extension + web app. Save any article while browsing, get automatic AI summaries and tags, then query your entire library in natural language.

## Features

- **Chrome Extension** — one-click article capture using Readability.js
- **AI Enrichment** — automatic summaries and tags generated asynchronously via GPT-4o-mini
- **RAG Q&A** — ask questions across your saved articles, get cited answers
- **Semantic Search** — pgvector cosine similarity search over article embeddings
- **Smart Tag Deduplication** — embedding-based merging of near-duplicate tags (e.g. "k8s" → "kubernetes")
- **Google OAuth** — sign in with Google on both web app and extension
- **Chat History** — all Q&A sessions saved and browsable

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL + pgvector |
| AI | OpenAI API (GPT-4o-mini + text-embedding-3-small) |
| Auth | JWT + Google OAuth |
| Extension | Chrome Manifest V3, Readability.js |

## Getting Started

### Prerequisites

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- PostgreSQL 16+ with pgvector extension
- Redis (used for rate limiting **and** the AI processing task queue — see below)
- OpenAI API key
- Google OAuth client ID (optional, for Google sign-in)

### Backend

```bash
cd backend
cp .env.example .env   # fill in DATABASE_URL, SECRET_KEY, OPENAI_API_KEY, REDIS_URL
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

API runs at `http://localhost:8000` — docs at `/docs`.

AI processing (summaries, tags, embeddings) runs on a separate **arq** worker process, backed by Redis. Run it alongside the API in a second terminal:

```bash
cd backend
uv run arq app.worker.WorkerSettings
```

> Redis was previously only used for rate limiting, which silently no-ops if Redis is unreachable. It's now a **hard** dependency for AI processing — without a running worker (or without Redis), saved articles stay at `status: "pending"` until the worker is available.

### Frontend

```bash
cd frontend
cp .env.example .env.local   # fill in NEXT_PUBLIC_API_URL, NEXT_PUBLIC_GOOGLE_CLIENT_ID
npm install
npm run dev
```

App runs at `http://localhost:3000`.

### Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `Cairn-extension/` folder

## Project Structure

```
Cairn/
├── backend/
│   ├── app/
│   │   ├── api/          # articles, auth, chat, users
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # AI service (embeddings, RAG, tag dedup)
│   │   └── core/         # config, database, security
│   ├── alembic/          # migrations
│   └── main.py
├── frontend/
│   ├── app/
│   │   ├── articles/     # Library page
│   │   ├── chat/         # Ask AI page
│   │   └── login/        # Auth page
│   ├── components/       # ArticleCard
│   └── lib/              # API client, auth utils
└── Cairn-extension/      # Chrome extension
    ├── popup.html/js/css
    ├── content.js
    └── lib/Readability.js
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/users/register` | Register |
| POST | `/api/auth/login` | Email/password login |
| POST | `/api/auth/google` | Google OAuth login |
| GET | `/api/articles` | List saved articles |
| POST | `/api/articles` | Save article |
| DELETE | `/api/articles/{id}` | Delete article |
| POST | `/api/chat/ask` | Ask a question (RAG) |
| GET | `/api/chat/history` | Chat history |
