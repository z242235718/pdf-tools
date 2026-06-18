import re
from datetime import datetime

# Characters that are invalid in Windows filenames
_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Maximum length of the base (name without extension)
_MAX_BASE_LENGTH = 80


def _sanitise(name: str) -> str:
    """Remove or replace characters that are unsafe in filenames."""
    # Replace path separators and control characters with underscore
    name = _INVALID_PATH_CHARS.sub("_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing dots, spaces and underscores
    name = name.strip(". _")
    return name if name else "output"


def build_output_filename(
    original_name: str,
    extension: str,
    timestamp: datetime | None = None,
    extra: str | None = None,
) -> str:
    """Build an output filename with a uniform timestamp suffix.

    Format (without *extra*)::

        output_<sanitised_base>_<timestamp>.<extension>

    Format (with *extra*)::

        output_<sanitised_base>_<extra>_<timestamp>.<extension>

    Examples:
        ``contract.pdf`` + ``pdf``
        → ``output_contract_20260613_153045.pdf``

        ``contract.pdf`` + ``pdf`` + fingerprint id
        → ``output_contract_abc123_20260613_153045.pdf``
    """
    ts = timestamp or datetime.now()
    ts_str = ts.strftime("%Y%m%d_%H%M%S")

    # Strip original extension
    base, *_ = original_name.rsplit(".", 1)
    base = _sanitise(base)[:_MAX_BASE_LENGTH]

    ext = extension.lstrip(".")

    parts = ["output", base]
    if extra:
        parts.append(extra)
    parts.append(ts_str)

    return f"{'_'.join(parts)}.{ext}"
