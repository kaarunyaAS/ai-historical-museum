from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    artifact_id: str | None = None
    language: str = "en"


class ChatReply(BaseModel):
    answer: str
    sources: list[dict]
    artifact_ids: list[str]
    citations: list[dict]
    retrieved_chunks: int
