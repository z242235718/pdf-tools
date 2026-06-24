"""Test configuration for integration tests.

Uses a temporary file-based SQLite database. Tables are created
once per session; rows are cleared between tests.

To ensure all modules that import ``SessionLocal`` directly
(e.g. ``from app.database import SessionLocal``) use the test
database, we temporarily replace the module-level ``SessionLocal``
on every affected module before the test session starts.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app

_db_file: Path | None = None


def _build_test_session() -> sessionmaker:
    global _db_file
    engine = create_engine(
        f"sqlite:///{_db_file}",
        connect_args={"check_same_thread": False},
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _setup_db() -> Generator:
    """Create a temp database file, all tables, and patch SessionLocal."""
    global _db_file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _db_file = Path(tmp.name)
    tmp.close()

    engine = create_engine(
        f"sqlite:///{_db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Patch every module that does `from app.database import SessionLocal`
    import app.database
    import app.pdf_engines.watermark
    import app.pdf_engines.pdf_to_word
    import app.pdf_engines.protect_pdf
    import app.pdf_engines.split_pdf
    import app.services.file_service
    import app.services.task_service
    import app.workers.task_runner

    app.database.SessionLocal = TestSession
    app.pdf_engines.watermark.SessionLocal = TestSession
    app.pdf_engines.pdf_to_word.SessionLocal = TestSession
    app.pdf_engines.protect_pdf.SessionLocal = TestSession
    app.pdf_engines.split_pdf.SessionLocal = TestSession
    app.services.file_service.SessionLocal = TestSession
    app.services.task_service.SessionLocal = TestSession
    app.workers.task_runner.SessionLocal = TestSession

    yield

    engine.dispose()
    _db_file.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _clean_tables() -> None:
    """Clear all rows before every test so tests are isolated."""
    engine = create_engine(
        f"sqlite:///{_db_file}",
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    engine.dispose()


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c
