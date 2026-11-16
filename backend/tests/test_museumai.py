import json
from pathlib import Path

import pytest

from app.config import Settings
from app.services.chunking import chunk_artifact
from app.services.gemini_service import GeminiService, normalize_answer_text
from app.services.knowledge_catalog import ARTIFACTS
from app.services.rag_service import RAGService


@pytest.mark.parametrize(
    "slug",
    [
        "nataraja",
        "dancing_girl",
        "lion_capital",
        "konark_wheel",
        "gandharan_buddha",
        "sanchi_torana",
        "mughal_miniature",
        "tipu_sword",
        "harappan_figurine",
        "elephanta_trimurti",
    ],
)
def test_catalog_contains_required_artifacts(slug):
    assert slug in ARTIFACTS
    assert ARTIFACTS[slug]["artifact_id"]
    assert len(ARTIFACTS[slug]["sections"]) >= 3
    assert ARTIFACTS[slug]["sources"]


def test_chunking_creates_stable_sections():
    artifact = ARTIFACTS["nataraja"]
    chunks = chunk_artifact(artifact, chunk_size=700, overlap=120)
    assert chunks
    assert all("chunk_key" in chunk for chunk in chunks)
    assert all(chunk["metadata"]["artifact_id"] == artifact["artifact_id"] for chunk in chunks)


def test_settings_are_loaded_from_env():
    settings = Settings()
    assert settings.embedding_dimensions > 0
    assert settings.retrieval_top_k > 0
    assert settings.cors_origin_list


def test_gemini_embedding_compatibility_reduces_3072_to_768():
    values = [float(i) for i in range(3072)]
    compatible = GeminiService._normalize_embedding(values)
    assert len(compatible) == 768
    assert compatible[0] == 1.5
    assert compatible[-1] == 3069.5


def test_question_intent_detection_handles_varied_phrases():
    service = RAGService()
    assert service.infer_question_intent("When was the Nataraja created?")["intent"] == "historical"
    assert service.infer_question_intent("Who discovered the Dancing Girl?")["intent"] == "discovery"
    assert service.infer_question_intent("Why is the Lion Capital important?")["intent"] == "significance"
    assert service.infer_question_intent("What material was used?")["intent"] == "technical"
    assert service.infer_question_intent("How is it different from other sculptures?")["intent"] == "comparison"
    assert service.infer_question_intent("Where can I see it today?")["intent"] == "location"
    assert service.infer_question_intent("Why?")["intent"] == "followup"


def test_artifact_resolution_finds_relevant_artifact_without_keyword_template():
    service = RAGService()
    resolved = service.resolve_artifact_from_question("Tell me about the Chola Bronze Nataraja.")
    assert resolved == "nataraja"
    resolved = service.resolve_artifact_from_question("Where is the Konark Sun Temple Wheel displayed?")
    assert resolved == "konark_wheel"


def test_answer_normalization_removes_debug_markdown_noise():
    text = "**The Chola Bronze Nataraja**\n\n&#x20;This is a historical object.\n\n```json\n{\"debug\": true}\n```\n\nSource list: [1, 2]"
    cleaned = normalize_answer_text(text)
    assert "**" not in cleaned
    assert "&#x20;" not in cleaned
    assert "json" not in cleaned.lower()
    assert "Source list" in cleaned
