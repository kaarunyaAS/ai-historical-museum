from __future__ import annotations

import json
import re
from typing import Iterable

import httpx
import numpy as np

from app.config import get_settings


class GeminiService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def generation_model(self) -> str:
        return self.settings.gemini_generation_model

    @property
    def embedding_model(self) -> str:
        return self.settings.gemini_embedding_model

    @property
    def available(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def embed_text(self, text: str) -> list[float]:
        if not self.available:
            raise RuntimeError("Gemini API is not configured; real embeddings require GEMINI_API_KEY.")

        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT",
            "title": "museumai_chunk",
        }
        try:
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:embedContent?key={self.settings.gemini_api_key}",
                json=payload,
                timeout=12,
            )
            response.raise_for_status()
            values = response.json().get("embedding", {}).get("values")
            if not values:
                raise RuntimeError("Gemini returned no embedding values for the supplied chunk.")
            return self._normalize_embedding([float(value) for value in values])
        except Exception as exc:
            raise RuntimeError("Real Gemini embedding generation failed; no synthetic or random vectors are used.") from exc

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def generate(self, prompt: str) -> str:
        if not self.available:
            raise RuntimeError("Gemini API is not configured; live generation is unavailable.")

        candidates = list(dict.fromkeys([
            self.generation_model,
            "gemini-3.8-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
        ]))

        last_error: Exception | None = None
        for model_name in candidates:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.9,
                    "maxOutputTokens": 256,
                },
            }
            try:
                response = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.settings.gemini_api_key}",
                    json=payload,
                    timeout=25,
                )
                if response.status_code == 429 or response.status_code == 503:
                    last_error = RuntimeError(f"Gemini generation temporarily unavailable for {model_name}: {response.text[:250]}")
                    continue
                response.raise_for_status()
                candidates_payload = response.json().get("candidates") or []
                if not candidates_payload:
                    raise RuntimeError("Gemini returned no candidates for the generation request.")
                parts = candidates_payload[0].get("content", {}).get("parts", [])
                texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
                text = "\n".join(texts).strip()
                if not text:
                    raise RuntimeError("Gemini returned an empty answer.")
                return text
            except Exception as exc:  # pragma: no cover - network / API errors are runtime dependent
                last_error = exc
                continue

        if last_error:
            raise RuntimeError("Real Gemini generation failed; no synthetic fallback answer is used.") from last_error
        raise RuntimeError("Real Gemini generation failed; no synthetic fallback answer is used.")

    @staticmethod
    def _normalize_embedding(values: list[float]) -> list[float]:
        if not values:
            return []

        vector = [float(value) for value in values]
        if len(vector) == 768:
            return vector

        if len(vector) == 3072:
            return [sum(vector[index:index + 4]) / 4.0 for index in range(0, 3072, 4)]

        if len(vector) > 768:
            return vector[:768]

        return vector + [0.0] * (768 - len(vector))

    @staticmethod
    def _fallback_generate(prompt: str) -> str:
        return (
            "I can help with the museum artifact context, but the live Gemini model was not available. "
            "Please review the retrieved artifact details and source references below."
            if prompt else "No reply generated."
        )


def normalize_answer_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("&#x20;", " ").replace("&#x27;", "'")
    cleaned = cleaned.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"```(?:json|javascript|python|text)?\s*[\s\S]*?```", "\n", cleaned)
    cleaned = re.sub(r"```[\s\S]*?```", "\n", cleaned)
    cleaned = re.sub(r"(?i)\b(json|debug|raw output):?\s*\{.*?\}\s*", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?i)\b(?:source list|sources)\s*[:\-]?\s*(?:\[[^\n]*\]|\d+(?:,\s*\d+)*)", "Source list:", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"(?m)^\s*#+\s*.*$", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*]\s*", "• ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def build_answer_prompt(question: str, context: str, language: str = "en", conversation_history: list[dict] | None = None) -> str:
    language_guidance = {
        "en": "Answer in English.",
        "ta": "Answer in Tamil.",
        "hi": "Answer in Hindi.",
    }
    instruction = language_guidance.get(language, language_guidance["en"])
    history_text = ""
    if conversation_history:
        recent = conversation_history[-3:]
        history_text = "\n".join(f"- {item.get('role', 'user')}: {item.get('text', '')}" for item in recent if item.get("text"))
        if history_text:
            history_text = "\nConversation history:\n" + history_text + "\n"

    return (
        "You are a careful museum curator and historian. Use only the provided context. "
        "Do not invent facts or claim certainty where the sources are limited. "
        "Answer the user's actual question first, then provide the relevant historical context. "
        "When the question is a follow-up such as 'why', 'who made it', or 'tell me more', interpret it using the conversation history. "
        "Use simple but historically grounded language and adapt the answer structure to the question type. "
        f"{instruction} "
        "If the question asks for comparison across artifacts, compare only the artifacts mentioned in the context. "
        "If the evidence is limited, say so clearly and avoid unsupported claims.\n\n"
        f"{history_text}"
        "Context:\n"
        f"{context}\n\n"
        "Question: "
        f"{question}\n\n"
        "Return a well-formed answer in plain text with short paragraphs, bullets when useful, and no JSON or debug output."
    )


def serialize_sources(source_ids: list[int], sources: dict[int, dict]) -> list[dict]:
    records: list[dict] = []
    for source_id in source_ids:
        source = sources.get(source_id)
        if source:
            records.append({
                "source_id": source_id,
                "title": source.get("title"),
                "url": source.get("url"),
                "source_type": source.get("source_type"),
            })
    return records
