"""Limit/offset helpers shared by list endpoints."""

from app.schemas.common import PageMeta


def build_meta(total: int, limit: int, offset: int) -> PageMeta:
    return PageMeta(
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


def slice_range(limit: int, offset: int) -> tuple[int, int]:
    """Supabase `.range()` is inclusive on both ends."""
    return offset, offset + limit - 1
