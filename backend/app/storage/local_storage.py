import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class LocalStorage:
    """Manages file storage on the local filesystem.

    Uses UUID-based server-side keys so user-supplied filenames are never
    used as real paths.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or settings.storage_root).resolve()
        self._ensure_dirs()

    # -- directories -------------------------------------------------------

    @property
    def upload_dir(self) -> Path:
        return self._root / "uploads"

    @property
    def output_dir(self) -> Path:
        return self._root / "outputs"

    @property
    def tmp_dir(self) -> Path:
        return self._root / "tmp"

    def _ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # -- public helpers ----------------------------------------------------

    @staticmethod
    def generate_key() -> str:
        return uuid.uuid4().hex

    # -- upload files ------------------------------------------------------

    def store_upload(self, content: bytes, key: str | None = None) -> Path:
        """Save uploaded content to the upload directory."""
        key = key or self.generate_key()
        dest = self.upload_dir / key
        dest.write_bytes(content)
        return dest

    def upload_path(self, key: str) -> Path:
        return self.upload_dir / key

    # -- output files ------------------------------------------------------

    def store_output(self, content: bytes, key: str | None = None) -> Path:
        """Save output content to the output directory."""
        key = key or self.generate_key()
        dest = self.output_dir / key
        dest.write_bytes(content)
        return dest

    def output_path(self, key: str) -> Path:
        return self.output_dir / key

    # -- temp files --------------------------------------------------------

    def tmp_path(self, task_id: int | str, name: str = "") -> Path:
        """Return a temporary path scoped to *task_id*."""
        folder = self.tmp_dir / str(task_id)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / name if name else folder

    # -- deletion ----------------------------------------------------------

    def delete(self, key: str, kind: str = "upload") -> bool:
        dir_map = {"upload": self.upload_dir, "output": self.output_dir}
        path = dir_map.get(kind, self.upload_dir) / key
        if path.exists():
            path.unlink()
            return True
        return False

    # -- exists ------------------------------------------------------------

    def exists(self, key: str, kind: str = "upload") -> bool:
        dir_map = {"upload": self.upload_dir, "output": self.output_dir}
        path = dir_map.get(kind, self.upload_dir) / key
        return path.exists()
