# MuseumAI

MuseumAI is a historical RAG application for ten major Indian heritage artifacts, built around a FastAPI backend, structured knowledge base, and a lightweight museum dashboard frontend built with HTML5, CSS3, and vanilla JavaScript.

## Project structure

- `backend/app` — FastAPI application, config, and service-layer code
- `backend/app/static` — HTML, CSS, and JavaScript museum dashboard assets
- `backend/scripts` — ingestion and database inspection scripts
- `backend/tests` — automated validation tests
- `database/migrations` — additive SQL migration for Supabase retrieval tables
- `knowledge_base/artifacts` — local JSON research records for all ten artifacts
- `evaluation` — evaluation and inspection outputs

## Included artifacts

1. Chola Bronze Nataraja
2. Dancing Girl of Mohenjo-daro
3. Lion Capital of Ashoka
4. Konark Sun Temple Wheel
5. Gandharan Buddha Statue
6. Sanchi Stupa Torana Gateway
7. Mughal Miniature Painting
8. Tipu Sultan's Sword
9. Harappan Terracotta Figurine
10. Elephanta Trimurti Sculpture

## Runtime configuration

Create `backend/.env` locally before using live services. It must define:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY`

No environment file or credentials are included in this repository.

## Windows PowerShell setup

```powershell
# Run from the repository root.
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv311\Scripts\python.exe -m pip install -r backend\requirements.txt
```

```powershell
# Run from the repository root.
$env:PYTHONPATH = "backend"
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Then open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/static/index.html

## Run ingestion

```powershell
# Run from the repository root. This writes records to the configured Supabase project.
$env:PYTHONPATH = "backend"
.\.venv311\Scripts\python.exe backend\scripts\ingest_knowledge.py
```

This script adds MuseumAI knowledge records without deleting existing Supabase data and keeps the historical knowledge in a safe additive pattern.

## Run tests

```powershell
# Run from the repository root.
.\.venv311\Scripts\python.exe -m pytest backend\tests -q
```

## Frontend architecture

- `backend/app/static/index.html` — museum dashboard shell
- `backend/app/static/styles.css` — HTML5/CSS3 layout, responsive museum styling
- `backend/app/static/app.js` — vanilla JavaScript for artifact browsing, multilingual UI, chat, and citations

The frontend is served directly through FastAPI using static file routes. JavaScript interacts with the existing FastAPI endpoints for artifact listing, artifact details, chat, and health status.

## Notes

- Configure `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `GEMINI_API_KEY` only in the local `backend/.env` file.
- Retrieval requires real Gemini embeddings and Supabase pgvector; synthetic vectors and local fallback retrieval are not used.
- Historical knowledge is intentionally grounded in museum and heritage references packaged in the artifact catalog and the local JSON files.
