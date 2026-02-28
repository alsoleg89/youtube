# YouTube → Articles MVP

Convert YouTube videos (up to 2 hours) into publication-ready articles for Medium, Habr, and LinkedIn using AI-powered Map-Reduce pipeline with validation.

## Architecture

```
Client → Nginx (:80) → Frontend (Next.js :3000)
                      → Backend  (FastAPI :8000) → PostgreSQL (:5432)
                                                 → Redis (:6379)
                                                 → Celery Worker → OpenAI API
```

**Pipeline:** YouTube URL → Extract captions/audio → Transcribe (Whisper) → Chunk → Map (GPT-4o-mini) → Reduce (GPT-4o) → Validate (GPT-4o) → Approved / Needs Review

## Tech Stack

| Layer    | Technology                    |
|----------|-------------------------------|
| Frontend | Next.js 14, TypeScript, Tailwind |
| Backend  | FastAPI, SQLAlchemy 2.x, Alembic |
| Tasks    | Celery, Redis                 |
| Database | PostgreSQL 16                 |
| AI       | OpenAI GPT-4o / GPT-4o-mini   |
| Media    | yt-dlp, pydub, ffmpeg         |
| Proxy    | Nginx                         |
| Infra    | Docker Compose                |

## Quick Start

1. Clone the repository and create an `.env` file:

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

2. Start all services (local development):

```bash
cd infra
docker compose up --build
```

3. Run database migration:

```bash
docker compose exec backend alembic upgrade head
```

4. Access the app:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000/docs

## API Endpoints

| Method | Path                           | Description                        |
|--------|--------------------------------|------------------------------------|
| POST   | `/api/videos`                  | Submit a YouTube video URL         |
| GET    | `/api/videos/{id}`             | Get video status, progress, result |
| POST   | `/api/videos/{id}/regenerate`  | Retry generation (needs_review)    |
| GET    | `/api/health`                  | Health check                       |

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

- `OPENAI_API_KEY` — required, your OpenAI API key
- `DATABASE_URL` — async PostgreSQL connection string
- `SYNC_DATABASE_URL` — sync PostgreSQL connection string (Celery)
- `REDIS_URL` — Redis connection string
- `MAP_MODEL` / `REDUCE_MODEL` / `VALIDATION_MODEL` — OpenAI model names

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers
│   │   ├── core/           # Config, dependencies
│   │   ├── db/             # SQLAlchemy models, sessions
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # GeneratorService, ValidatorService, YouTubeService, TranscriptionService
│   │   ├── providers/      # LLM provider abstraction (OpenAI)
│   │   ├── workers/        # Celery tasks, pipeline
│   │   └── main.py
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js pages (home, video result)
│   │   ├── components/     # URLForm, StatusTracker, ResultTabs, CopyButton
│   │   ├── lib/            # API client, polling hook, constants
│   │   └── types/          # TypeScript interfaces
│   └── package.json
├── infra/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml       # Local development
│   ├── docker-compose.prod.yml  # Yandex Cloud production
│   └── nginx.conf
├── .env.example
├── README.md
└── README_YANDEX.md             # Yandex Cloud deployment guide (RU)
```
