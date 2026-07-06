from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    database_url: str = "postgresql://lead:lead@localhost:55433/lead_enricher"
    fetch_timeout_sec: int = 15
    use_playwright: bool = False
    hot_score_threshold: int = 80
    warm_score_threshold: int = 50
    cache_ttl_hours: int = 24
    use_fixture_fetcher: bool = False
    max_text_chars: int = 8000
    llm_temperature: float = 0.1
    llm_max_retries: int = 2


settings = Settings()
