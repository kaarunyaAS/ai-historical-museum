"""Split artifact knowledge into stable, section-aware chunks."""

from __future__ import annotations

import re
from typing import Any


META_PREFIX = "[[museumai]]"


def clean_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long(paragraph, chunk_size, overlap))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            tail = current[-overlap:].strip() if overlap and current else ""
            current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def _split_long(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[.?!])\s+", text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current:
                pieces.append(current.strip())
                current = ""
            start = 0
            while start < len(sentence):
                end = min(start + chunk_size, len(sentence))
                pieces.append(sentence[start:end].strip())
                if end == len(sentence):
                    break
                start = max(end - overlap, start + 1)
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                pieces.append(current.strip())
            current = sentence
    if current:
        pieces.append(current.strip())
    return pieces


def chunk_artifact(artifact: dict[str, Any], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    if chunk_size < 200:
        raise ValueError("chunk_size must be at least 200 characters")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    name = artifact["name"]
    artifact_id = artifact["artifact_id"]
    default_sources = [source["source_id"] for source in artifact.get("sources", [])]
    produced: list[dict[str, Any]] = []

    sections = list(artifact.get("sections") or [])
    timeline = artifact.get("timeline") or []
    if timeline:
        lines = []
        for item in timeline:
            certainty = item.get("certainty") or "stated"
            lines.append(f"{item.get('date', 'Undated')} ({certainty}): {item.get('event', '').strip()}")
        sections.append(
            {
                "id": "timeline",
                "title": "Historical timeline",
                "text": "\n".join(lines),
                "source_ids": default_sources,
            }
        )

    index = 0
    for section in sections:
        body = clean_text(section.get("text") or "")
        if not body:
            continue
        source_ids = section.get("source_ids") or default_sources
        parts = split_paragraphs(body, chunk_size, overlap)
        for part_index, part in enumerate(parts):
            chunk_key = f"museumai-{artifact_id}-{section['id']}-{part_index:03d}"
            content = f"{name}. Section: {section.get('title', section['id'])}.\n\n{part}"
            produced.append(
                {
                    "chunk_key": chunk_key,
                    "section_id": section["id"],
                    "chunk_index": index,
                    "content": content,
                    "source_ids": source_ids,
                    "metadata": {
                        "artifact_id": artifact_id,
                        "section_title": section.get("title"),
                        "part_index": part_index,
                    },
                }
            )
            index += 1
    return produced


def pack_chunk_text(chunk: dict[str, Any]) -> str:
    """Keep source metadata recoverable even before optional columns exist."""
    import json

    meta = {
        "chunk_key": chunk["chunk_key"],
        "section_id": chunk["section_id"],
        "source_ids": chunk["source_ids"],
    }
    return f"{META_PREFIX}{json.dumps(meta, ensure_ascii=False)}\n{chunk['content']}"


def unpack_chunk_text(chunk_text: str) -> tuple[str, dict[str, Any]]:
    import json

    if not chunk_text.startswith(META_PREFIX):
        return chunk_text, {}
    first, _, rest = chunk_text.partition("\n")
    try:
        meta = json.loads(first[len(META_PREFIX) :])
    except json.JSONDecodeError:
        meta = {}
    return rest, meta
