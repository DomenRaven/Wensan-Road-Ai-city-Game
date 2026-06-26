# Start GameForge FastAPI backend (dev)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "backend")

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    .\.venv\Scripts\pip install -r requirements.txt
}

Write-Host "API: http://127.0.0.1:8000/docs"
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
