from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/youtube"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/youtube"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""

    llm_model: str = "gpt-4o"
    llm_mini_model: str = "gpt-4o-mini"
    transcription_model: str = "whisper-1"

    llm_provider: str = "openai"
    local_llm_base_url: str = "http://host.docker.internal:11434/v1"
    local_llm_model: str = "llama3.1"
    local_llm_mini_model: str = "qwen2.5:0.5b"

    map_model: str = ""
    reduce_model: str = ""
    validation_model: str = ""

    max_video_duration: int = 7200
    max_chunks: int = 120
    max_upload_bytes: int = 10 * 1024 * 1024
    tmp_dir: str = "/tmp/app"

    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _apply_model_routing(self) -> Self:
        if self.llm_provider == "local_ollama":
            self.map_model = self.local_llm_mini_model
            self.reduce_model = self.local_llm_model
            self.validation_model = self.local_llm_model
        else:
            self.map_model = self.llm_mini_model
            self.reduce_model = self.llm_mini_model
            self.validation_model = self.llm_mini_model
        return self


settings = Settings()
