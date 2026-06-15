"""Page-range parsing utilities.

All user-facing page numbers are 1-based.  Internal indices returned by
:func:`parse_page_range` are 0-based.
"""

_PAGE_RANGE_INVALID = "PAGE_RANGE_INVALID"


def parse_page_range(value: str, total_pages: int) -> list[int]:
    """Parse a user-supplied page range string into a sorted list of
    0-based page indices.

    Supported input formats: ``all``, ``1``, ``1-5``, ``1,3,5``,
    ``1-3,8,10-12``.

    Raises:
        ValueError: with ``PAGE_RANGE_INVALID`` error code on invalid input.
    """
    if not value or not value.strip():
        raise ValueError(_PAGE_RANGE_INVALID, "Page range is empty")

    value = value.strip()

    if value == "all":
        return list(range(total_pages))

    pages: set[int] = set()
    parts = [p.strip() for p in value.split(",")]

    for part in parts:
        if not part:
            raise ValueError(_PAGE_RANGE_INVALID, f"Empty segment in '{value}'")

        if "-" in part:
            # Range: N-M
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise ValueError(
                    _PAGE_RANGE_INVALID, f"Invalid range '{part}' in '{value}'"
                ) from None

            if start < 1 or end < 1:
                raise ValueError(
                    _PAGE_RANGE_INVALID,
                    f"Page numbers must be >= 1, got '{part}'",
                )
            if start > end:
                raise ValueError(
                    _PAGE_RANGE_INVALID,
                    f"Reverse range '{part}' in '{value}'",
                )
            if end > total_pages:
                raise ValueError(
                    _PAGE_RANGE_INVALID,
                    f"Page {end} exceeds total {total_pages}",
                )
            for p in range(start, end + 1):
                pages.add(p - 1)  # convert to 0-based
        else:
            # Single page
            try:
                page = int(part)
            except ValueError:
                raise ValueError(
                    _PAGE_RANGE_INVALID, f"Invalid page '{part}' in '{value}'"
                ) from None
            if page < 1:
                raise ValueError(
                    _PAGE_RANGE_INVALID,
                    f"Page numbers must be >= 1, got '{page}'",
                )
            if page > total_pages:
                raise ValueError(
                    _PAGE_RANGE_INVALID,
                    f"Page {page} exceeds total {total_pages}",
                )
            pages.add(page - 1)

    return sorted(pages)


def compute_remaining_pages(delete_pages: list[int], total_pages: int) -> list[int]:
    """Return the 0-based page indices that are **not** in *delete_pages*.

    Raises:
        ValueError: if every page would be deleted (result would be empty).
    """
    remaining = [p for p in range(total_pages) if p not in set(delete_pages)]
    if not remaining:
        raise ValueError(
            _PAGE_RANGE_INVALID,
            "Cannot delete all pages — at least one page must remain",
        )
    return remaining
