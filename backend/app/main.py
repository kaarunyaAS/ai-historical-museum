from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.rag_service import RAGService
from app.services.supabase_service import SupabaseService
from app.services.knowledge_catalog import ARTIFACTS, ARTIFACT_ORDER

settings = get_settings()
app = FastAPI(title="MuseumAI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = RAGService()
supabase_service = SupabaseService()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    artifact_id: str | None = None
    language: str = "en"
    conversation_history: list[dict[str, str]] | None = None


class IngestRequest(BaseModel):
    artifact_id: str | None = None
    refresh: bool = False


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "supabase": supabase_service.healthcheck(),
        "gemini": {"configured": rag_service.gemini.available, "model": settings.gemini_generation_model},
        "artifact_count": len(ARTIFACT_ORDER),
    }


@app.get("/api/artifacts")
async def artifact_list() -> dict:
    items = rag_service.list_artifacts()
    return {"artifacts": items, "count": len(items)}


@app.get("/api/artifacts/{slug}")
async def artifact_detail(slug: str) -> dict:
    artifact = rag_service.get_artifact(slug)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    try:
        answer = rag_service.answer_question(
            request.question,
            request.artifact_id,
            request.language,
            request.conversation_history,
        )
        return answer
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"RAG retrieval failed: {exc}") from exc


@app.post("/api/ingest")
async def ingest(request: IngestRequest | None = None) -> dict:
    requested_artifact = (request.artifact_id if request else None)
    if requested_artifact:
        artifact = ARTIFACTS.get(requested_artifact)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"status": "not_implemented_for_single_artifact", "artifact_id": requested_artifact}
    return {"status": "ready", "message": "Use the backend ingestion script to populate Supabase knowledge documents.", "artifact_count": len(ARTIFACT_ORDER)}


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
