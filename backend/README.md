# PDF Tools Backend

## Development

```powershell
cd E:\Work\Coding\pdf-tools\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Checks

```powershell
$env:RUFF_CACHE_DIR="..\.cache\ruff"
$env:PYTEST_ADDOPTS="-o cache_dir=../.cache/pytest"
python -m ruff check .
python -m pytest
```
