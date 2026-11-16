from __future__ import annotations

import os

import httpx
import pytest
from fastapi.testclient import TestClient

import app.services.rag_service as rag_service_module
from app.main import app, rag_service
from app.services.chunking import pack_chunk_text
from app.services.knowledge_catalog import ARTIFACTS
from app.services.supabase_service import SupabaseService


client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert 'supabase' in payload
    assert 'gemini' in payload


def test_artifact_listing():
    response = client.get('/api/artifacts')
    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] >= 10
    assert len(payload['artifacts']) >= 10


@pytest.fixture
def offline_rag_dependencies(monkeypatch):
    artifact = ARTIFACTS["nataraja"]
    source_id = artifact["sources"][0]["source_id"]
    section = artifact["sections"][0]
    chunk = {
        "chunk_key": "offline-test-chunk",
        "section_id": section["id"],
        "source_ids": [source_id],
        "content": section["text"][:200],
    }
    row = {
        "chunk_id": 1,
        "document_id": 1,
        "artifact_id": artifact["artifact_id"],
        "chunk_index": 0,
        "chunk_text": pack_chunk_text(chunk),
        "section_id": chunk["section_id"],
        "source_ids": [source_id],
        "similarity": 0.9,
    }

    def fake_match_knowledge_chunks(**kwargs):
        assert len(kwargs["query_embedding"]) == 768
        assert kwargs["filter_artifact_ids"] == [artifact["artifact_id"]]
        return [row]

    monkeypatch.setattr(rag_service_module, "local_embedding", lambda _text: [0.1] * 768)
    monkeypatch.setattr(SupabaseService, "configured", property(lambda _service: True))
    monkeypatch.setattr(rag_service.supabase, "match_knowledge_chunks", fake_match_knowledge_chunks)
    monkeypatch.setattr(rag_service.gemini, "generate", lambda _prompt: "The Nataraja represents Shiva's cosmic dance.")

    source = artifact["sources"][0]
    return {
        "artifact_id": artifact["artifact_id"],
        "source": {
            "source_id": source_id,
            "title": source.get("title"),
            "url": source.get("url"),
            "source_type": source.get("source_type"),
        },
    }


def test_chat_endpoint(offline_rag_dependencies):
    response = client.post('/api/chat', json={'question': 'What is the significance of the Nataraja?', 'artifact_id': 'nataraja', 'language': 'en'})
    assert response.status_code == 200
    assert response.json() == {
        "answer": "The Nataraja represents Shiva's cosmic dance.",
        "sources": [offline_rag_dependencies["source"]],
        "artifact_ids": [offline_rag_dependencies["artifact_id"]],
        "citations": [offline_rag_dependencies["source"]],
        "retrieved_chunks": 1,
    }


def test_supabase_is_reachable():
    url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        return
    response = httpx.get(
        f'{url}/rest/v1/artifacts',
        headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Accept': 'application/json'},
        params={'select': '*', 'limit': '1'},
        timeout=30,
    )
    assert response.status_code == 200
