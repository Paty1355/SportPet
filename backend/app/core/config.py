from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "HackYeah API"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    chroma_path: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 10

    # Klucz endpointów serwisowych (generator danych). Bez niego są wyłączone (503).
    service_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Azure OpenAI – bez endpointu i klucza backend działa na atrapie LLM i lokalnych embeddingach Chromy
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_vision_deployment: str | None = None  # None → ten sam deployment co chat
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    @property
    def azure_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


settings = Settings()
