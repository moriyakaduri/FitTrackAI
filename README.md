# FitTrackAI

FitTrackAI is a Hebrew PySide6 desktop app for daily nutrition and fitness
tracking. The GUI talks to a local FastAPI backend. Meals, weights, and
workouts are stored in cloud SQL Server. Local Ollama models provide Hebrew
text advice and food-image analysis. Images are uploaded to Cloudinary.
Packaged products can be looked up by barcode through OpenFoodFacts.

AI values are estimates. Nothing is saved until the user confirms the meal,
weight, or workout entry.

## Where to show each requirement

| Requirement | Open this |
|---|---|
| MVP | `mvp/` |
| Microfrontends | `mvp/view/features/` |
| MVC | `backend/mvc/` |
| CQRS | `backend/cqrs/` |
| Event Sourcing | `backend/event_sourcing/` |
| Gateway | `backend/gateway/` |
| Cursor Skill | `.cursor/skills/fittrack-safe-change/` |
| PRD / PIV | `docs/PRD.md`, `docs/PIV.md` |

Desktop entry: `python gui_main.py`. API entry: `uvicorn backend.main:app`.

## Main capabilities

- Login, Hebrew dashboard, charts, and meal details
- Search local nutrition facts and articles
- Log meals, body weight, and workouts as append-only events
- OpenFoodFacts barcode lookup into the meal form
- DictaLM advisor with SQL-keyword RAG
- LLaVA food-image analysis into editable meal fields
- Image chat: photo plus a user question, grounded with RAG
- Cloudinary `secure_url` on both image flows

## Architecture summary

```text
mvp/view (PySide6) -> mvp/presenter -> FastAPI (backend/main.py)
        -> backend/cqrs commands/queries -> SQL Server
        -> backend/mvc/controllers (login, AI)
        -> backend/gateway -> Ollama / Cloudinary / OpenFoodFacts
```

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Technology stack

| Area | Implementation |
|---|---|
| Desktop | Python 3.10, PySide6, QtCharts |
| API | FastAPI, uvicorn |
| Database | Microsoft SQL Server on Somee, SQLAlchemy, pyodbc |
| AI runtime | Ollama in Docker Compose (`gpus: all` when NVIDIA is available) |
| Text model | `aminadaven/dictalm2.0-instruct:q4_k_m` |
| Vision model | `llava` |
| Images | Cloudinary |
| Barcode | OpenFoodFacts |

## Prerequisites

- Windows 10 or 11
- Python 3.10 (64-bit)
- Microsoft ODBC Driver 17 or 18 for SQL Server
- Docker Desktop with Linux containers
- Access to the shared SQL Server
- A Cloudinary account for image upload
- NVIDIA GPU is optional. Compose requests it; CPU-only Ollama still runs and
  is slower.

## Setup

From PowerShell in the repository root:

```powershell
py -3.10 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with placeholders replaced by your values. Variable names only
belong in git (`.env.example`). The backend loads `.env` automatically;
existing process or Windows environment variables take precedence.

Required names:

- `FITTRACK_DB_USER`, `FITTRACK_DB_PASS`, `FITTRACK_DB_SERVER`, `FITTRACK_DB_NAME`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

## Run

1. Start Ollama:

```powershell
docker compose up -d ollama
docker compose exec ollama ollama list
```

Pull only missing models:

```powershell
docker compose exec ollama ollama pull aminadaven/dictalm2.0-instruct:q4_k_m
docker compose exec ollama ollama pull llava
```

2. Start FastAPI:

```powershell
python -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

3. In a second activated terminal, start the GUI:

```powershell
python -B gui_main.py
```

Verify the API at `http://127.0.0.1:8000/docs`.

Ollama GPU notes: [`docs/OLLAMA_DOCKER.md`](docs/OLLAMA_DOCKER.md).

## Project structure

- `gui_main.py` — desktop entry and dashboard composition shell
- `mvp/view/features/` — authentication, AI, data-entry, trends, motivation
- `mvp/presenter/` — MVP presenter, login worker, meal-save worker
- `mvp/model/` — desktop API URL/timeouts (not the SQLAlchemy entities)
- `backend/main.py` — FastAPI composition root
- `backend/mvc/models/` — SQLAlchemy entities including `UserEvent`
- `backend/mvc/controllers/` — login and AI HTTP controllers
- `backend/cqrs/` — command and query routers
- `backend/event_sourcing/` — locator for the activity event log
- `backend/gateway/` — Ollama, Cloudinary, OpenFoodFacts
- `backend/database/` — SQLAlchemy engine and sessions
- `compose.yaml` — Ollama service, persistent volume, optional GPU request
- `.cursor/skills/fittrack-safe-change/` — project Cursor Skill
- `docs/` — PRD, architecture, PIV, Ollama instructions

## Deeper documentation

- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [PIV evidence](docs/PIV.md)
- [Ollama in Docker](docs/OLLAMA_DOCKER.md)
