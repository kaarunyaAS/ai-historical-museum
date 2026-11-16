from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

from app.services.chunking import chunk_artifact, unpack_chunk_text
from app.services.gemini_service import GeminiService, build_answer_prompt, normalize_answer_text, serialize_sources
from app.services.knowledge_catalog import ARTIFACTS, ARTIFACT_ORDER
from app.services.supabase_service import SupabaseService


def local_embedding(text: str) -> list[float]:
    gemini = GeminiService()
    if not gemini.available:
        raise RuntimeError("A real Gemini embedding model is required for retrieval; no synthetic vectors are used.")
    return gemini.embed_text(text)


class RAGService:
    def __init__(self) -> None:
        self.gemini = GeminiService()
        self.supabase = SupabaseService()
        self.source_lookup: dict[int, dict] = {}
        for artifact in ARTIFACTS.values():
            for item in artifact["sources"]:
                self.source_lookup[int(item["source_id"])] = item

    def infer_question_intent(self, question: str) -> dict[str, Any]:
        text = (question or "").strip().lower()
        if not text:
            return {"intent": "general", "confidence": 0.0}

        if len(text.split()) <= 2:
            if any(token in text for token in ["why", "who", "what", "where", "when", "how"]):
                return {"intent": "followup", "confidence": 0.8}

        if any(token in text for token in ["when", "date", "century", "period", "created", "built", "made"]):
            return {"intent": "historical", "confidence": 0.9}
        if any(token in text for token in ["who discovered", "found", "discovered", "excavated", "identified"]) :
            return {"intent": "discovery", "confidence": 0.9}
        if any(token in text for token in ["why", "importance", "significance", "important", "meaning", "symbolism", "purpose"]):
            return {"intent": "significance", "confidence": 0.9}
        if any(token in text for token in ["material", "made of", "crafted", "technique", "medium", "bronze", "stone", "terracotta", "metal", "wood"]):
            return {"intent": "technical", "confidence": 0.85}
        if any(token in text for token in ["compare", "difference", "different", "versus", "contrast", "similar", "unlike", "between"]):
            return {"intent": "comparison", "confidence": 0.9}
        if any(token in text for token in ["where", "location", "found", "display", "today", "museum", "site", "seen", "visit"]):
            return {"intent": "location", "confidence": 0.9}
        if any(token in text for token in ["who", "whom", "owner", "made it", "made by"]):
            return {"intent": "followup", "confidence": 0.8}
        if any(token in text for token in ["tell me more", "explain", "describe", "complete history", "full history", "details"]):
            return {"intent": "detailed", "confidence": 0.8}
        return {"intent": "general", "confidence": 0.7}

    def resolve_artifact_from_question(self, question: str, artifact_slug: str | None = None) -> str | None:
        if artifact_slug and artifact_slug in ARTIFACTS:
            return artifact_slug
        normalized = (question or "").lower()

        candidates: list[tuple[str, int]] = []
        for slug, artifact in ARTIFACTS.items():
            name = artifact["name"].lower()
            alias_tokens = {slug, name}
            alias_tokens |= {segment.lower() for segment in name.split()}
            alias_tokens |= {"nataraja", "dancing girl", "lion capital", "konark", "gandhara", "sanchi", "mughal", "tipu", "harappan", "elephanta"}
            if any(token in normalized for token in alias_tokens):
                score = sum(1 for token in alias_tokens if token in normalized)
                candidates.append((slug, score))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[1], reverse=True)
        if candidates[0][1] <= 0:
            return None
        return candidates[0][0]

    def list_artifacts(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for slug in ARTIFACT_ORDER:
            artifact = ARTIFACTS[slug]
            output.append(
                {
                    "id": artifact["artifact_id"],
                    "slug": artifact["slug"],
                    "name": artifact["name"],
                    "description": artifact["description"],
                    "source_count": len(artifact["sources"]),
                }
            )
        return output

    def get_artifact(self, slug: str) -> dict[str, Any] | None:
        artifact = ARTIFACTS.get(slug)
        if not artifact:
            return None
        return {
            "id": artifact["artifact_id"],
            "slug": artifact["slug"],
            "name": artifact["name"],
            "description": artifact["description"],
            "sources": artifact["sources"],
            "sections": artifact["sections"],
        }

    def retrieve(self, question: str, artifact_slug: str | None = None, top_k: int = 6, threshold: float = 0.15) -> list[dict[str, Any]]:
        normalized_slug = artifact_slug
        if normalized_slug and normalized_slug not in ARTIFACTS:
            normalized_slug = next((slug for slug, artifact in ARTIFACTS.items() if artifact["artifact_id"] == normalized_slug), None)

        resolved_question_artifact = self.resolve_artifact_from_question(question)
        if normalized_slug is None and resolved_question_artifact:
            normalized_slug = resolved_question_artifact

        query_embedding = local_embedding(question)
        if not self.supabase.configured:
            raise RuntimeError("Supabase is configured but not available for pgvector retrieval.")

        filter_artifact_ids = None
        if normalized_slug:
            filter_artifact_ids = [ARTIFACTS[normalized_slug]["artifact_id"]]

        rows = self.supabase.match_knowledge_chunks(
            query_embedding=query_embedding,
            match_count=top_k,
            filter_artifact_ids=filter_artifact_ids,
            similarity_threshold=threshold,
        )

        scored: list[dict[str, Any]] = []
        seen_chunk_keys: set[str] = set()
        for row in rows:
            content, meta = unpack_chunk_text(row.get("chunk_text") or "")
            artifact_id = row.get("artifact_id")
            if not artifact_id:
                continue

            artifact = next((item for item in ARTIFACTS.values() if item["artifact_id"] == artifact_id), None)
            if artifact is None:
                continue
            if normalized_slug and artifact["slug"] != normalized_slug:
                continue

            chunk_key = meta.get("chunk_key") or row.get("chunk_key") or f"{row.get('document_id')}-{row.get('chunk_id')}"
            if chunk_key in seen_chunk_keys:
                continue
            seen_chunk_keys.add(chunk_key)

            source_ids = meta.get("source_ids") or row.get("source_ids") or []
            scored.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_name": artifact["name"],
                    "source_ids": source_ids,
                    "content": content,
                    "section_id": meta.get("section_id") or row.get("section_id") or "retrieved",
                    "chunk_key": chunk_key,
                    "score": float(row.get("similarity") or 0.0),
                }
            )

        scored.sort(key=lambda row: row["score"], reverse=True)
        return scored[:top_k]

    def answer_question(self, question: str, artifact_slug: str | None = None, language: str = "en", conversation_history: list[dict] | None = None) -> dict[str, Any]:
        resolved_artifact = self.resolve_artifact_from_question(question, artifact_slug)
        chunks = self.retrieve(question, artifact_slug=resolved_artifact, top_k=3, threshold=0.12)
        if not chunks:
            if resolved_artifact:
                return {
                    "answer": "I could not verify enough evidence for this question from the available historical records for this artifact. I can try a more specific question or a different artifact.",
                    "sources": [],
                    "artifact_ids": [ARTIFACTS[resolved_artifact]["artifact_id"]],
                    "citations": [],
                    "retrieved_chunks": 0,
                }
            return {
                "answer": "I could not find a sufficiently relevant historical match for this question in the current MuseumAI knowledge base. Please ask about a specific artifact or provide more context.",
                "sources": [],
                "artifact_ids": [],
                "citations": [],
                "retrieved_chunks": 0,
            }

        context_parts = []
        unique_artifacts = set()
        for chunk in chunks:
            unique_artifacts.add(chunk["artifact_id"])
            excerpt = chunk["content"]
            if len(excerpt) > 700:
                excerpt = excerpt[:700].rstrip() + "..."
            context_parts.append(f"Artifact: {chunk['artifact_name']} ({chunk['artifact_id']})\nSection: {chunk['section_id']}\n{excerpt}")

        prompt = build_answer_prompt(question, "\n\n".join(context_parts), language, conversation_history)
        try:
            answer = self.gemini.generate(prompt)
        except Exception as exc:
            return {
                "answer": "I could not generate a verified answer because the live Gemini generation service is currently unavailable. The retrieved historical evidence is still listed below, and the cited sources can be reviewed directly.",
                "sources": [],
                "artifact_ids": sorted(unique_artifacts),
                "citations": [],
                "retrieved_chunks": len(chunks),
                "error": str(exc),
            }

        answer = normalize_answer_text(answer)
        citations = []
        for chunk in chunks:
            for entry in serialize_sources(chunk["source_ids"], self.source_lookup):
                citations.append(entry)

        seen = set()
        deduped = []
        for item in citations:
            key = (item["source_id"], item["title"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return {
            "answer": answer,
            "sources": deduped,
            "artifact_ids": sorted(unique_artifacts),
            "citations": deduped,
            "retrieved_chunks": len(chunks),
        }


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_arr = np.asarray(left, dtype=float)
    right_arr = np.asarray(right, dtype=float)
    left_norm = np.linalg.norm(left_arr)
    right_norm = np.linalg.norm(right_arr)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return float(np.dot(left_arr, right_arr) / (left_norm * right_norm))
