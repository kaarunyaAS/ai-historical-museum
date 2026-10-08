# Museum Project

Project workspace for the museum application.

## Structure

- `backend/` — backend entry point, API routes, and services
- `frontend/` — frontend application
- `artifact_detection/` — artifact detection components
- `rag/` — retrieval-augmented generation components
- `voice/` — voice-related components
- `talking_portrait/` — talking portrait components
- `historical_videos/` — historical video components
- `database/` — database-related resources
- `data/` — project data
- `models/` — model files and resources
- `tests/` — project tests

## Windows setup

Use Python 3.11 for the project environment. From the project directory:

```powershell
if (-not (Test-Path .venv)) { uv venv --python 3.11 .venv }
.\.venv\Scripts\Activate.ps1
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Install FFmpeg once, then open a new PowerShell window so its PATH is refreshed:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Start the backend from the project directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/app/` for the museum chat, or
`http://127.0.0.1:8000/` to check the API. The first transcription loads the
multilingual Whisper `base` model. Whisper detects the spoken language
automatically; transcription quality varies by language, audio quality, and
model size. Gemini remains configured as `gemini-3.5-flash-lite`.
