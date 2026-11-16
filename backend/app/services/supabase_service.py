from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings


class SupabaseService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return self.settings.supabase_configured

    def healthcheck(self) -> dict[str, Any]:
        if not self.configured:
            return {"status": "missing_env", "connected": False, "tables": []}

        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Accept": "application/json",
        }
        try:
            response = httpx.get(
                f"{self.settings.supabase_url.rstrip('/')}/rest/v1/",
                headers=headers,
                timeout=30,
            )
            if response.status_code != 200:
                return {"status": "error", "connected": False, "http_status": response.status_code}
            return {"status": "ok", "connected": True, "host": self.settings.supabase_url.rstrip('/').split('//')[-1]}
        except Exception as exc:
            return {"status": "exception", "connected": False, "error": str(exc)[:300]}

    def fetch_artifacts(self) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        headers = self._headers()
        response = httpx.get(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/artifacts",
            headers=headers,
            params={"select": "*", "order": "id.asc"},
            timeout=30,
        )
        if response.status_code != 200:
            return []
        return response.json() or []

    def fetch_knowledge_documents(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        response = httpx.get(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/knowledge_documents",
            headers=self._headers(),
            params={"select": "*", "limit": str(limit)},
            timeout=30,
        )
        if response.status_code != 200:
            return []
        return response.json() or []

    def fetch_knowledge_chunks(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        response = httpx.get(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/knowledge_chunks",
            headers=self._headers(),
            params={"select": "*", "limit": str(limit)},
            timeout=60,
        )
        if response.status_code != 200:
            return []
        return response.json() or []

    def match_knowledge_chunks(
        self,
        query_embedding: list[float],
        match_count: int,
        filter_artifact_ids: list[str] | None = None,
        similarity_threshold: float = 0.1,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError("Supabase is not configured for pgvector retrieval.")

        payload: dict[str, Any] = {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "similarity_threshold": similarity_threshold,
        }
        if filter_artifact_ids:
            payload["filter_artifact_ids"] = filter_artifact_ids

        response = httpx.post(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/rpc/match_knowledge_chunks",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Supabase pgvector retrieval failed: "
                f"status={response.status_code} body={response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Supabase pgvector retrieval returned invalid JSON.") from exc

        if not isinstance(data, list):
            raise RuntimeError("Supabase pgvector retrieval returned an unexpected payload shape.")
        return data

    def fetch_sources(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        response = httpx.get(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/sources",
            headers=self._headers(),
            params={"select": "*", "limit": str(limit)},
            timeout=30,
        )
        if response.status_code != 200:
            return []
        return response.json() or []

    def insert_document(self, document: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return {"status": "skipped", "reason": "Missing Supabase config"}

        response = httpx.post(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/knowledge_documents",
            headers={**self._headers(), "Prefer": "return=representation"},
            json=document,
            timeout=30,
        )
        if response.status_code not in (200, 201, 204):
            return {"status": "error", "http_status": response.status_code, "body": response.text[:500]}
        body = response.json() if response.content else []
        return {"status": "ok", "body": body}

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.configured:
            return {"status": "skipped", "reason": "Missing Supabase config"}

        response = httpx.post(
            f"{self.settings.supabase_url.rstrip('/')}/rest/v1/knowledge_chunks",
            headers={**self._headers(), "Prefer": "return=representation"},
            json=chunks,
            timeout=60,
        )
        if response.status_code not in (200, 201, 204):
            return {"status": "error", "http_status": response.status_code, "body": response.text[:1000]}
        body = response.json() if response.content else []
        return {"status": "ok", "count": len(chunks), "body": body}

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Accept": "application/json",
        }


def ensure_document_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "artifact_id": item["artifact_id"],
        "title": item.get("title") or item.get("name") or "MuseumAI artifact",
        "content": item.get("content") or item.get("text") or "",
        "document_type": item.get("document_type", "museumai_rag"),
    }
    if item.get("source_id") is not None:
        payload["source_id"] = item["source_id"]
    if item.get("created_at"):
        payload["created_at"] = item["created_at"]
    return payload
