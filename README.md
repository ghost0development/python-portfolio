# Portfolio API

![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)
![GraphQL](https://img.shields.io/badge/GraphQL-Strawberry-E10098?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat-square)
![Cloudflare Tunnel](https://img.shields.io/badge/Cloudflare%20Tunnel-✓-F38020?style=flat-square)

**Unified FastAPI backend: URL Shortener + GraphQL Blog + more. One API, one deploy, shared auth.**

## Modules

| Module | Status | Tech | Endpoint |
|--------|--------|------|----------|
| **Auth** | ✅ | JWT + SHA-256 | `/auth/*` |
| **URL Shortener** | ✅ | REST API | `/api/shortener/*` |
| **GraphQL Blog** | ✅ | Strawberry | `/api/blog` |
| AI Chat Proxy | ⬜ | SSE + OpenAI | `/api/chat/*` |
| Async Task Queue | ⬜ | WebSocket | `/api/queue/*` |
| RAG PDF Q&A | ⬜ | LangChain + ChromaDB | `/api/rag/*` |

## Quick Start

```bash
git clone https://github.com/voicenotesite/python-portfolio.git
cd python-portfolio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Open [http://localhost:8002/docs](http://localhost:8002/docs)

## API Overview

### Auth

```bash
curl -X POST http://localhost:8002/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","username":"alice","password":"secret123"}'

TOKEN=$(curl -s -X POST http://localhost:8002/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"secret123"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
```

### URL Shortener

```bash
curl -X POST "http://localhost:8002/api/shortener/shorten?target_url=https://github.com" \
  -H "Authorization: Bearer $TOKEN"
```

### GraphQL Blog

```graphql
mutation {
  createPost(input: { title: "Hello", content: "World", published: true }) {
    id title content
  }
}

query {
  posts { id title content author { username } }
}
```

## Deploy

```bash
# Via Cloudflare Tunnel (no account needed)
cloudflared tunnel --url http://localhost:8002

# Or with systemd persistence
systemd-run --user --unit=portfolio-api \
  --working-directory=$(pwd) \
  -p Restart=on-failure \
  venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## Architecture

```
Client → Cloudflare Tunnel → FastAPI (port 8002)
                                ├── /auth        (JWT)
                                ├── /api/shortener (REST)
                                ├── /api/blog     (GraphQL)
                                ├── /api/chat     (SSE)
                                ├── /api/queue    (WS)
                                └── /api/rag      (REST)
                                       └── SQLite (SQLAlchemy)
```

## Project Status

Portfolio series **3/5** completed:
- ✅ [URL Shortener](https://github.com/voicenotesite/FastAPI-url)
- ✅ [GraphQL Blog](https://github.com/voicenotesite/graphql-blog)
- ✅ **Portfolio API (merged)**
- ⬜ AI Chat Proxy
- ⬜ Async Task Queue
- ⬜ RAG PDF Q&A

## License

MIT
