# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PDF Tools 32-bit EXE (Python 3.11 32-bit)."""

import os
import sys
from pathlib import Path

block_cipher = None

SPEC_DIR = Path(SPECPATH).resolve()  # type: ignore[name-defined]
BACKEND_DIR = SPEC_DIR
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if not FRONTEND_DIST.is_dir():
    sys.stderr.write(f"[spec] Frontend dist not found: {FRONTEND_DIST}\n")
    sys.exit(1)

datas = [
    (str(FRONTEND_DIST), "frontend/dist"),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "pymupdf",
    "pdf2docx",
    "pdf2docx.converter",
    "pdf2docx.layout",
    "pdf2docx.page",
    "pdf2docx.table",
    "pdf2docx.text",
    "img2pdf",
    "qrcode",
    "qrcode.image.pil",
    "sqlalchemy.dialects.sqlite",
    "alembic",
    "cryptography",
    "lxml",
    "lxml._elementpath",
    "lxml.etree",
    "fire",
    "numpy",
    "cv2",
    "PIL",
    "PIL._imaging",
]

excludes = [
    "tkinter",
    "matplotlib",
    "numpy.tests",
    "pytest",
    "ruff",
    "mypy",
    "pandas",
    "scipy",
    "torch",
    "tensorflow",
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
    name="pdf-tools-x86",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch="x86",  # force 32-bit bootloader
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
    name="pdf-tools-x86",
)
