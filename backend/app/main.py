from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import files, previews, tasks, trace

app = FastAPI(title="PDF Tools API", version="0.1.0")

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(previews.router, prefix="/api/previews", tags=["previews"])
app.include_router(trace.router, prefix="/api/trace", tags=["trace"])
