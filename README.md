# api-main

The backend service for [ivanpashkulev.com](https://ivanpashkulev.com) — a FastAPI application powered by an AI agent that acts as Ivan Pashkulev, answering questions about his career, skills, and experience in real time via streaming.

## Overview

This service exposes a single streaming endpoint that receives a user message and conversation history, passes it through a LangGraph agent backed by OpenAI's `gpt-4o-mini` model, and streams the response back token by token using Server-Sent Events (SSE).

The AI agent is seeded with context documents (CV, bio, summaries) loaded from the `assets/` directory at startup. This gives the model accurate, up-to-date information about Ivan without fine-tuning.

## Architecture

The project follows **Screaming Architecture** (Clean Architecture by Robert C. Martin) — the folder structure reflects the domain, not the framework.

```
src/ivanpashkulev/
├── core/
│   └── config.py          # Application settings via pydantic-settings
├── chat/
│   ├── router.py          # FastAPI route definitions
│   ├── service.py         # LangGraph agent, document loading, SSE streaming
│   ├── schemas.py         # Pydantic request/response models
│   └── dependencies.py    # Dependency injection (singleton ChatService)
└── main.py                # FastAPI app bootstrap, CORS, router registration
```

**Request flow:**
```
POST /chat
  └── router.py         receives ChatRequest (message + history)
  └── service.py        builds message list, runs LangGraph agent
  └── LangGraph         invokes the ChatOpenAI node
  └── OpenAI            streams tokens from gpt-4o-mini
  └── StreamingResponse yields SSE chunks back to the client
```

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| AI Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM | [OpenAI](https://openai.com/) — `gpt-4o-mini` |
| LLM Integration | [langchain-openai](https://python.langchain.com/docs/integrations/chat/openai/) |
| Document Loading | [PyMuPDF](https://pymupdf.readthedocs.io/) (PDF), plain text |
| Configuration | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Package Manager | [uv](https://docs.astral.sh/uv/) |
| Python Version | 3.14 |

## Key Design Decisions

**Streaming over polling** — The `/chat` endpoint always streams using `StreamingResponse` with `media_type="text/event-stream"`. There is no non-streaming fallback. This provides a real-time typing experience in the frontend.

**Singleton service** — `ChatService` is instantiated once via `@lru_cache` in `dependencies.py`. This means documents are loaded and the LangGraph graph is compiled once at startup, not on every request.

**Hosted LLM** — The application uses OpenAI's API and reads the API key and model name from environment variables. The API key is kept outside the source code.

**No database** — Conversation history is passed by the client on every request. The backend is stateless.

## Local Development

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key

### Setup

```bash
# Install dependencies
uv sync
```

### Environment Variables

Create a `.env` file at the project root:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
```

### Run

```bash
uv run uvicorn ivanpashkulev.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

### Assets

Place context documents in the `assets/` directory. Supported formats:

- `.pdf` — loaded via PyMuPDF
- `.txt` / `.md` — loaded as plain text

These files are intentionally excluded from version control (`.gitignore`) as they contain personal information.

## API

### `POST /chat`

Streams an AI response as Server-Sent Events.

**Request body:**
```json
{
  "message": "What is your experience with Python?",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! I'm Ivan..." }
  ]
}
```

**Response:** `text/event-stream`
```
data: I have been

data:  working with Python

data:  for over 5 years...

data: [DONE]
```

## Docker

The service is containerised using a multi-step build that separates dependency installation from source copying for optimal layer caching.

```bash
docker build -t api-main .
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/assets:/app/assets \
  api-main
```

## CI/CD

Pushing to `main` triggers a GitHub Actions workflow that:

1. Builds and pushes a Docker image to `ghcr.io/ivanpashkulev/api-main` tagged with the commit SHA
2. Opens an automated pull request on the [devops](https://github.com/ivanpashkulev/devops) repository updating the image tag in `docker-compose.yml`

The deployment is completed by merging that PR and running `docker compose pull && docker compose up -d` on the server.
