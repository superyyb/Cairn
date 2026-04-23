# 🍴 ForkMark

> AI-powered knowledge management for developers — built as a Chrome extension with semantic search and team collaboration.

ForkMark helps developers stop losing technical articles in browser bookmarks. Save any article with one click, let AI auto-summarize and tag it, then query your personal knowledge base in natural language.

> ⚠️ **Status**: Currently in active development (Week 1 of 8). This repository contains the **backend API** built with FastAPI + PostgreSQL.

## ✨ Features

### Implemented (Week 1)
- 🔐 User authentication with JWT (register / login)
- 🛡️ Bcrypt password hashing
- 👤 Protected user profile endpoint
- 📊 Auto-generated OpenAPI documentation
- 🗄️ Database migrations with Alembic

### Roadmap
- 📥 Chrome extension for one-click article saving (Week 2)
- 🤖 AI-powered summarization and auto-tagging (Week 2)
- 🔍 Hybrid search: keyword + semantic (Week 3-4)
- 💬 Natural language Q&A on your knowledge base via RAG (Week 4)
- 👥 Team workspaces with shared knowledge (Week 5)
- 🌐 Production deployment (Week 6)
- 🧠 **v2.0**: Knowledge graph with entity & relation extraction (Week 7-8)

## 🏗️ Tech Stack

**Backend**
- Python 3.11 + FastAPI
- PostgreSQL 16 + pgvector
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- python-jose (JWT)
- passlib + bcrypt (password hashing)
- Pydantic v2 (validation)
- uv (package manager)

**Coming Soon**
- OpenAI API (embeddings + chat)
- Redis (caching)
- Next.js 14 (web frontend)
- Chrome Extension Manifest V3

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. **Clone the repository**
```bash
   git clone https://github.com/superyyb/forkmark.git
   cd forkmark
```

2. **Install dependencies**
```bash
   uv sync
```

3. **Set up the database**
```bash
   # Create database and user (in psql)
   CREATE DATABASE devvault;
   CREATE USER devvault_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE devvault TO devvault_user;
```

4. **Configure environment**
```bash
   cp .env.example .env
   # Edit .env with your database URL and secret key
```

5. **Run database migrations**
```bash
   uv run alembic upgrade head
```

6. **Start the development server**
```bash
   uv run uvicorn main:app --reload
```

7. **Explore the API**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📁 Project Structure
forkmark/
├── alembic/              # Database migrations
├── app/
│   ├── api/              # API route handlers
│   │   ├── auth.py       # Login endpoint
│   │   └── users.py      # User CRUD endpoints
│   ├── core/             # Core utilities
│   │   ├── config.py     # Settings management
│   │   ├── database.py   # SQLAlchemy session
│   │   └── security.py   # JWT + password hashing
│   ├── models/           # SQLAlchemy ORM models
│   │   └── user.py
│   └── schemas/          # Pydantic request/response schemas
│       ├── auth.py
│       └── user.py
├── main.py               # Application entry point
├── pyproject.toml        # Dependencies (uv)
└── .env.example          # Environment template

## 🎯 API Endpoints

| Method | Path                    | Auth   | Description                  |
|--------|-------------------------|--------|------------------------------|
| POST   | `/api/users/register`   | ❌      | Register a new user          |
| POST   | `/api/auth/login`       | ❌      | Login and receive JWT token  |
| GET    | `/api/users/me`         | ✅      | Get current user profile     |
| GET    | `/api/users/count`      | ✅      | Total registered users       |
| GET    | `/health`               | ❌      | Health check                 |

Full interactive docs at `/docs` when the server is running.

## 🧪 Testing the API

```bash
# Register
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret12345","username":"alice"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=alice@example.com&password=secret12345"
# Returns: {"access_token":"eyJ...","token_type":"bearer"}

# Get current user
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🗺️ Development Roadmap

This project follows an 8-week development plan:

- **Week 1** ✅ Backend foundation: Auth, DB, JWT
- **Week 2** ⏳ Chrome extension + article saving
- **Week 3** ⏳ Web frontend (Next.js)
- **Week 4** ⏳ AI features: embeddings + RAG
- **Week 5** ⏳ Team workspaces
- **Week 6** ⏳ Production deployment
- **Week 7-8** ⏳ Knowledge graph upgrade (v2.0)
