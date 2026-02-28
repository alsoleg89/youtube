import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OLLAMA_TAGS_PATH = "/api/tags"


def check_ollama_ready() -> None:
    """Verify that Ollama is reachable and required models are pulled."""
    base = settings.local_llm_base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]

    tags_url = f"{base}{_OLLAMA_TAGS_PATH}"
    required = {settings.local_llm_model, settings.local_llm_mini_model}

    try:
        resp = httpx.get(tags_url, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {tags_url} — {exc}\n"
            "Make sure Ollama is running on your host machine: "
            "https://ollama.com/download"
        ) from exc

    available = {m["name"].split(":")[0] for m in resp.json().get("models", [])}
    available_full = {m["name"] for m in resp.json().get("models", [])}
    all_known = available | available_full

    missing = [m for m in required if m not in all_known and m.split(":")[0] not in all_known]
    if missing:
        cmds = " && ".join(f"ollama pull {m}" for m in missing)
        raise RuntimeError(
            f"Required model(s) not found in Ollama: {', '.join(missing)}\n"
            f"Pull them on your host machine:\n  {cmds}"
        )

    logger.info(
        "Ollama preflight OK — models available: %s",
        ", ".join(sorted(required)),
    )
