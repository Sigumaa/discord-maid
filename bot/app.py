from __future__ import annotations

import asyncio
import logging
import os

from .config import Settings, load_settings
from .discord_bot import GrokDiscordBot
from .grok_client import GrokClient
from .log_store import read_guild_log_tail
from .memory import InMemoryBackend, MemoryBackend
from .names import resolve_call_name
from .types import ChatMessage


def main() -> None:
    level_name = os.getenv("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, level_name, logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = load_settings()
    logging.getLogger(__name__).info(
        "Settings loaded model=%s api_host=%s max_history=%s data_dir=%s allowed_guilds=%s bootstrap_lines=%s",
        settings.model,
        settings.api_host,
        settings.max_history,
        settings.data_dir,
        sorted(settings.allowed_guild_ids),
        settings.bootstrap_log_lines,
    )
    grok = GrokClient(
        api_key=settings.x_api_key,
        api_host=settings.api_host,
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
    memory = InMemoryBackend(settings.max_history)
    asyncio.run(_bootstrap_memory(settings, memory))
    bot = GrokDiscordBot(settings=settings, grok=grok, memory=memory)
    bot.run(settings.discord_bot_token)


async def _bootstrap_memory(settings: Settings, memory: MemoryBackend) -> None:
    max_lines = settings.bootstrap_log_lines
    if max_lines <= 0:
        return

    for guild_id in settings.allowed_guild_ids:
        entries = await read_guild_log_tail(settings.data_dir, guild_id, max_lines)
        channel_histories: dict[tuple[int | None, int], list[ChatMessage]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            channel_id = entry.get("channel_id")
            if role not in ("user", "assistant") or not isinstance(channel_id, int):
                continue
            key = (guild_id, channel_id)
            history = channel_histories.setdefault(key, [])
            content = entry.get("content")
            if not isinstance(content, str):
                content = ""
            if role == "user":
                user_id = entry.get("user_id")
                if not isinstance(user_id, int):
                    continue
                display_name = entry.get("display_name")
                if not isinstance(display_name, str):
                    display_name = "user"
                preferred_name = entry.get("preferred_name")
                preferred_value = (
                    preferred_name if isinstance(preferred_name, str) else None
                )
                call_name = resolve_call_name(
                    user_id=user_id,
                    special_user_id=settings.special_user_id,
                    display_name=display_name,
                    preferred_name=preferred_value,
                )
                content = f"{call_name} (id: {user_id}): {content}"
            history.append({"role": role, "content": content})

        for mem_key, history in channel_histories.items():
            if len(history) > settings.max_history:
                history = history[-settings.max_history :]
            memory.load_history(mem_key, history)
