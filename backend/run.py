"""PDF Tools single-exe launcher.

When frozen by PyInstaller, the bundled layout is::

    pdf-tools-x64.exe            # this entry point
    _internal/                   # PyInstaller onedir contents
    frontend/dist/               # extracted static assets

When unfrozen (dev), the launcher is a no-op shim that just runs uvicorn.
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        stream=sys.stdout,
    )


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _bundle_root() -> Path:
    """Directory holding the EXE / onedir payload (NOT _MEIPASS for onefile)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _meipass_root() -> Path:
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[arg-type]
    return Path(__file__).resolve().parent


def _pick_port(preferred: int = 8000) -> int:
    """Try preferred, fall back to an ephemeral free port."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            if candidate == 0:
                return sock.getsockname()[1]
            return candidate
    return preferred


def _wait_for_server(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _open_browser(url: str) -> None:
    def _go() -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:  # pragma: no cover
            logging.warning("Failed to open browser: %s", exc)

    threading.Thread(target=_go, daemon=True).start()


def _resolve_storage_root() -> Path:
    """Storage must live next to the EXE so users can find/clean outputs."""
    if env := os.environ.get("PDF_TOOLS_STORAGE_ROOT"):
        return Path(env).expanduser().resolve()
    root = _bundle_root() / "storage"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_database_url() -> str:
    if env := os.environ.get("PDF_TOOLS_DATABASE_URL"):
        return env
    db_path = _bundle_root() / "pdf_tools.db"
    # forward slashes work for sqlite on Windows too
    return f"sqlite:///{db_path.as_posix()}"


def _configure_environment(frontend_dist: Path) -> int:
    storage_root = _resolve_storage_root()
    db_url = _resolve_database_url()
    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "production")
    os.environ["DATABASE_URL"] = db_url
    os.environ["STORAGE_ROOT"] = str(storage_root)
    os.environ["PDF_TOOLS_FRONTEND_DIST"] = str(frontend_dist)

    port = int(os.environ.get("PDF_TOOLS_PORT", "8000"))
    port = _pick_port(port)
    host = os.environ.get("PDF_TOOLS_HOST", "127.0.0.1")
    os.environ["PDF_TOOLS_RESOLVED_PORT"] = str(port)
    return port


def _get_app():
    # Import after env is configured so module-level create_app() picks up our
    # environment (PDF_TOOLS_FRONTEND_DIST, etc.).
    from app.main import app  # noqa: PLC0415

    return app


def main() -> int:
    _configure_logging()
    log = logging.getLogger("pdf-tools.launcher")

    meipass = _meipass_root()
    bundle = _bundle_root()
    frontend_dist = meipass / "frontend" / "dist"
    if not frontend_dist.exists():
        # Unfrozen dev: fall back to the repo's built dist.
        alt = bundle / "frontend" / "dist"
        if alt.exists():
            frontend_dist = alt

    port = _configure_environment(frontend_dist)
    host = os.environ.get("PDF_TOOLS_HOST", "127.0.0.1")
    base_url = f"http://{host}:{port}"

    log.info("PDF Tools starting at %s", base_url)
    log.info("Frontend assets: %s", frontend_dist)
    log.info("Storage root: %s", os.environ["STORAGE_ROOT"])
    log.info("Database: %s", os.environ["DATABASE_URL"])

    import uvicorn

    app = _get_app()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("UVICORN_LOG_LEVEL", "info"),
        access_log=False,
    )
    server = uvicorn.Server(config)

    def _post_start() -> None:
        if _wait_for_server(host, port, timeout=30.0):
            log.info("Server is up. Opening browser...")
            _open_browser(base_url)
        else:  # pragma: no cover
            log.error("Server did not become ready within 30s")

    threading.Thread(target=_post_start, daemon=True).start()

    try:
        server.run()
    except KeyboardInterrupt:  # pragma: no cover
        log.info("Interrupted, shutting down...")
        server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
