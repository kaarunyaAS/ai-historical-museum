"""Environment configuration. Secrets are read from the environment only."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base" / "artifacts"


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    gemini_api_key: str = ""
    gemini_generation_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    chunk_size: int = 1400
    chunk_overlap: int = 200
    retrieval_top_k: int = 6
    relevance_threshold: float = 0.5
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    supabase_db_url: str = ""
    document_type: str = "museumai_rag"

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Database primary keys discovered by inspecting this Supabase project on
# 13 November 2026. The application does not rename those rows.
ARTIFACT_DB_IDS: dict[str, str] = {
    "nataraja": "ART001",
    "dancing_girl": "ART002",
    "lion_capital": "ART003",
    "konark_wheel": "ART004",
    "gandharan_buddha": "ART005",
    "sanchi_torana": "ART006",
    "mughal_miniature": "ART007",
    "tipu_sword": "ART008",
    "harappan_figurine": "ART009",
    "elephanta_trimurti": "ART010",
}

DB_ID_TO_SLUG = {value: key for key, value in ARTIFACT_DB_IDS.items()}
