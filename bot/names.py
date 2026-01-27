from __future__ import annotations

RESERVED_NAMES = {"しゆい"}


def normalize_preferred_name(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        return ""
    wrappers = [
        ("「", "」"),
        ("『", "』"),
        ('"', '"'),
        ("'", "'"),
        ("`", "`"),
    ]
    for start, end in wrappers:
        if stripped.startswith(start) and stripped.endswith(end) and len(stripped) > 1:
            return stripped[len(start) : -len(end)].strip()
    return stripped


def is_reserved_name(name: str) -> bool:
    normalized = normalize_preferred_name(name)
    return any(
        normalized == reserved or normalized.startswith(reserved)
        for reserved in RESERVED_NAMES
    )


def resolve_call_name(
    *,
    user_id: int,
    special_user_id: int,
    display_name: str,
    preferred_name: str | None,
) -> str:
    if user_id == special_user_id:
        return "しゆい"
    candidate = preferred_name or display_name
    candidate = normalize_preferred_name(candidate)
    if not candidate or is_reserved_name(candidate):
        return f"ユーザー{user_id}"
    return candidate
