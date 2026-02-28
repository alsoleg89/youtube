import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.sources import router as sources_router
from app.core.config import settings
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.llm_provider == "local_ollama":
        from app.providers.ollama_preflight import check_ollama_ready

        check_ollama_ready()
    yield


app = FastAPI(title="Content Hub", version="0.2.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
