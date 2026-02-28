from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/youtube"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/youtube"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    map_model: str = "gpt-4o-mini"
    reduce_model: str = "gpt-4o"
    validation_model: str = "gpt-4o"

    max_video_duration: int = 7200
    max_chunks: int = 120
    tmp_dir: str = "/tmp/app"

    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
