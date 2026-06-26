# GameForge K12 Backend

FastAPI orchestration layer: Session pool, wizard API, play variant resolver.

## Quick start (Windows)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify:

```powershell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/sessions
```

OpenAPI docs: http://127.0.0.1:8000/docs

## Redis

- Preferred: local Redis at `redis://127.0.0.1:6379/0`
- Dev fallback: if Redis unavailable, uses **in-memory** store (`session_backend: memory` in `/health`)

## Deployment TBD

| Env | Default |
|-----|---------|
| `DEPLOYMENT_SERVER_OS` | `TBD` |
| `DEPLOYMENT_TERMINAL_LAYOUT` | `TBD` |

## API summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + session stats |
| POST | `/sessions` | Create session (429 if full) |
| GET | `/sessions` | List active sessions |
| GET | `/wizard/steps` | Wizard step enum |
| GET | `/genres` | Genre registry |
| POST | `/sessions/{id}/wizard/{step}` | Submit wizard step |
