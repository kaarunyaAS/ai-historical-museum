from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.services.chunking import chunk_artifact, pack_chunk_text
from app.services.gemini_service import GeminiService
from app.services.knowledge_catalog import ARTIFACTS
from app.services.supabase_service import SupabaseService, ensure_document_payload


ROOT = Path(__file__).resolve().parents[2]
settings = get_settings()
service = SupabaseService()
gemini = GeminiService()


def build_document_records():
    documents = []
    for slug, artifact in ARTIFACTS.items():
        full_text = "\n\n".join(section["text"] for section in artifact["sections"])
        documents.append(
            {
                "artifact_id": artifact["artifact_id"],
                "title": artifact["name"],
                "content": full_text,
                "document_type": "museumai_rag",
                "source_id": artifact["sources"][0]["source_id"],
            }
        )
    return documents


def resolve_valid_source_id(artifact: dict) -> int | None:
    valid_ids = {int(item["id"]) for item in service.fetch_sources() if item.get("id") is not None}
    for entry in artifact.get("sources", []):
        source_id = int(entry.get("source_id"))
        if source_id in valid_ids:
            return source_id
    if valid_ids:
        return min(valid_ids)
    return None


def build_chunk_records() -> list[dict]:
    chunks = []
    for artifact in ARTIFACTS.values():
        for piece in chunk_artifact(artifact, settings.chunk_size, settings.chunk_overlap):
            chunks.append(
                {
                    "chunk_key": piece["chunk_key"],
                    "document_id": None,
                    "artifact_id": artifact["artifact_id"],
                    "chunk_index": piece["chunk_index"],
                    "chunk_text": piece["content"],
                    "section_id": piece["section_id"],
                    "source_ids": piece["source_ids"],
                    "embedding": gemini.embed_text(piece["content"]),
                }
            )
    return chunks


def main() -> int:
    if not service.configured:
        print("SUPABASE_MISSING")
        return 1

    existing = service.fetch_knowledge_documents(limit=200)
    existing_by_artifact = {
        item.get("artifact_id"): item
        for item in existing
        if item.get("artifact_id") and item.get("document_type") == "museumai_rag"
    }

    print(f"existing_documents={len(existing)}")
    for artifact in ARTIFACTS.values():
        source_id = resolve_valid_source_id(artifact)
        document = ensure_document_payload({
            "artifact_id": artifact["artifact_id"],
            "title": artifact["name"],
            "content": "\n\n".join(section["text"] for section in artifact["sections"]),
            "document_type": "museumai_rag",
            "source_id": source_id,
        })

        if artifact["artifact_id"] in existing_by_artifact:
            print(f"SKIP_DOCUMENT {artifact['artifact_id']}")
            continue

        result = service.insert_document(document)
        print(f"INSERT_DOCUMENT {artifact['artifact_id']} => {result.get('status')}")

    documents_after = service.fetch_knowledge_documents(limit=200)
    docs_by_artifact = {
        item.get("artifact_id"): item
        for item in documents_after
        if item.get("artifact_id") and item.get("document_type") == "museumai_rag"
    }

    for artifact in ARTIFACTS.values():
        artifact_id = artifact["artifact_id"]
        if artifact_id not in docs_by_artifact:
            print(f"MISSING_AFTER_INSERT {artifact_id}")
            continue
        record = docs_by_artifact[artifact_id]
        for chunk in chunk_artifact(artifact, settings.chunk_size, settings.chunk_overlap):
            try:
                embedding = gemini.embed_text(chunk["content"])
                payload = {
                    "document_id": record["id"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": pack_chunk_text(chunk),
                    "embedding": embedding,
                }
                service.insert_chunks([payload])
                print(f"INSERT_CHUNK {artifact_id}:{chunk['chunk_key']}")
            except Exception as exc:
                print(f"CHUNK_ERROR {artifact_id}:{chunk['chunk_key']} {type(exc).__name__}:{str(exc)[:200]}")

    print("INGESTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
