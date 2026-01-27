from __future__ import annotations

import asyncio
import json
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable


def _guild_dir(base_dir: str, guild_id: int | None) -> str:
    if guild_id is None:
        return os.path.join(base_dir, "dm")
    return os.path.join(base_dir, f"guild_{guild_id}")


def _user_log_path(base_dir: str, guild_id: int | None, user_id: int) -> str:
    return os.path.join(_guild_dir(base_dir, guild_id), "users", f"{user_id}.log.jsonl")


def _user_meta_path(base_dir: str, guild_id: int | None, user_id: int) -> str:
    return os.path.join(_guild_dir(base_dir, guild_id), "users", f"{user_id}.meta.json")


def _guild_log_path(base_dir: str, guild_id: int | None) -> str:
    return os.path.join(_guild_dir(base_dir, guild_id), "guild.log.jsonl")


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_entry(
    *,
    guild_id: int | None,
    channel_id: int,
    user_id: int,
    display_name: str,
    role: str,
    content: str,
    message_id: int | None,
    preferred_name: str | None = None,
) -> dict[str, Any]:
    entry = {
        "ts": _now_iso(),
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "display_name": display_name,
        "role": role,
        "content": content,
        "message_id": message_id,
    }
    if preferred_name:
        entry["preferred_name"] = preferred_name
    return entry


async def append_logs(base_dir: str, entry: dict[str, Any]) -> None:
    guild_path = _guild_log_path(base_dir, entry["guild_id"])
    user_path = _user_log_path(base_dir, entry["guild_id"], entry["user_id"])

    def _write() -> None:
        _ensure_parent(guild_path)
        _ensure_parent(user_path)
        line = json.dumps(entry, ensure_ascii=False)
        with open(guild_path, "a", encoding="utf-8") as guild_file:
            guild_file.write(line + "\n")
        with open(user_path, "a", encoding="utf-8") as user_file:
            user_file.write(line + "\n")

    await asyncio.to_thread(_write)


async def read_user_meta(
    base_dir: str, guild_id: int | None, user_id: int
) -> dict[str, Any]:
    path = _user_meta_path(base_dir, guild_id, user_id)

    def _read() -> dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                return {}
        if isinstance(data, dict):
            return data
        return {}

    return await asyncio.to_thread(_read)


async def write_user_meta(
    base_dir: str, guild_id: int | None, user_id: int, data: dict[str, Any]
) -> None:
    path = _user_meta_path(base_dir, guild_id, user_id)

    def _write() -> None:
        _ensure_parent(path)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    await asyncio.to_thread(_write)


async def read_user_log_tail(
    base_dir: str, guild_id: int | None, user_id: int, max_lines: int
) -> list[dict[str, Any]]:
    path = _user_log_path(base_dir, guild_id, user_id)

    def _read() -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        lines = list(deque(_iter_lines(path), maxlen=max_lines))
        return [entry for entry in _parse_lines(lines) if entry is not None]

    return await asyncio.to_thread(_read)


async def read_guild_log_tail(
    base_dir: str, guild_id: int | None, max_lines: int
) -> list[dict[str, Any]]:
    path = _guild_log_path(base_dir, guild_id)

    def _read() -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        lines = list(deque(_iter_lines(path), maxlen=max_lines))
        return [entry for entry in _parse_lines(lines) if entry is not None]

    return await asyncio.to_thread(_read)


def _iter_lines(path: str) -> Iterable[str]:
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                yield stripped


def _parse_lines(lines: Iterable[str]) -> list[dict[str, Any] | None]:
    entries: list[dict[str, Any] | None] = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            entry = None
        entries.append(entry)
    return entries


def pick_entries(
    entries: list[dict[str, Any]], pick_count: int | None
) -> list[dict[str, Any]]:
    if pick_count is None or pick_count <= 0:
        return entries
    if len(entries) <= pick_count:
        return entries
    return entries[-pick_count:]


def format_entries(entries: Iterable[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        ts = entry.get("ts")
        name = entry.get("preferred_name") or entry.get("display_name")
        role = entry.get("role")
        content = entry.get("content")
        lines.append(f"[{ts}] {name} ({role}): {content}")
    return "\n".join(lines)
