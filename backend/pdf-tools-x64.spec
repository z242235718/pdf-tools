# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PDF Tools 64-bit EXE."""

import os
import sys
from pathlib import Path

block_cipher = None

# Project layout (absolute paths from spec location)
SPEC_DIR = Path(SPECPATH).resolve()  # type: ignore[name-defined]
BACKEND_DIR = SPEC_DIR  # spec lives in backend/
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

# Sanity check
if not FRONTEND_DIST.is_dir():
    sys.stderr.write(f"[spec] Frontend dist not found: {FRONTEND_DIST}\n")
    sys.exit(1)

# Collect data files: (source, destination-relative-to-_MEIPASS)
datas = [
    (str(FRONTEND_DIST), "frontend/dist"),
]

# Hidden imports we know are needed
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn workers",
    "pymupdf",
    "pdf2docx",
    "img2pdf",
    "qrcode",
    "sqlalchemy.dialects.sqlite",
    "alembic",
]

# Exclude modules we never need to ship
excludes = [
    "tkinter",
    "matplotlib",
    "numpy.tests",
    "pytest",
    "ruff",
    "mypy",
]

a = Analysis(
    [str(BACKEND_DIR / "run.py")],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdf-tools-x64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="pdf-tools-x64",
)
