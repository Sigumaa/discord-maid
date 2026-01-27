from __future__ import annotations

import asyncio
import logging
import re
from typing import Iterable

import discord
from discord import app_commands

from .config import Settings
from .grok_client import GrokClient
from .log_store import (
    append_logs,
    build_entry,
    pick_entries,
    read_user_log_tail,
    read_user_meta,
    write_user_meta,
)
from .names import is_reserved_name, normalize_preferred_name, resolve_call_name
from .memory import ConversationKey, MemoryBackend
from .types import ChatMessage


def _strip_bot_mention(content: str, bot_id: int) -> str:
    pattern = re.compile(rf"<@!?{bot_id}>")
    return pattern.sub("", content, count=1).strip()


def _chunk_text(text: str, limit: int = 1900) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _conversation_key(message: discord.Message) -> ConversationKey:
    guild_id = message.guild.id if message.guild else None
    return (guild_id, message.channel.id)


_RECALL_PATTERN = re.compile(
    r"(?:^|\\s)(?:/|#)?recall\\s+(\\d+)(?:\\s+(\\d+))?",
    re.IGNORECASE,
)
_SYNC_PATTERN = re.compile(r"^(?:/|#)?sync\\b", re.IGNORECASE)
_HELP_PATTERN = re.compile(r"^(?:/|#)?(help|ヘルプ|使い方)\\b", re.IGNORECASE)

_PREFERRED_NAME_PATTERNS = [
    re.compile(r"(.+?)って呼んでほしい"),
    re.compile(r"(.+?)と呼んでほしい"),
    re.compile(r"(.+?)で呼んでほしい"),
    re.compile(r"(.+?)って読んでほしい"),
    re.compile(r"(.+?)と読んでほしい"),
    re.compile(r"(.+?)って呼称してほしい"),
    re.compile(r"(.+?)と呼称してほしい"),
    re.compile(r"(.+?)で呼称してほしい"),
]


def _extract_recall_request(content: str) -> tuple[int, int | None] | None:
    match = _RECALL_PATTERN.search(content)
    if not match:
        return None
    lines = int(match.group(1))
    pick = int(match.group(2)) if match.group(2) else None
    return (lines, pick)


def _strip_recall_command(content: str) -> str:
    return _RECALL_PATTERN.sub("", content).strip()


def _has_auto_recall_trigger(content: str, keywords: list[str]) -> bool:
    return any(keyword in content for keyword in keywords)


def _extract_preferred_name(content: str) -> str | None:
    stripped = content.strip()
    for pattern in _PREFERRED_NAME_PATTERNS:
        match = pattern.search(stripped)
        if not match:
            continue
        candidate = match.group(1).strip()
        if candidate:
            return candidate
    return None


class GrokDiscordBot(discord.Client):
    def __init__(
        self,
        settings: Settings,
        grok: GrokClient,
        memory: MemoryBackend,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._settings = settings
        self._grok = grok
        self._memory = memory
        self._locks: dict[ConversationKey, asyncio.Lock] = {}
        self._synced = False
        self.tree = app_commands.CommandTree(self)
        self.tree.add_command(
            app_commands.Command(
                name="help",
                description="使い方を表示します",
                callback=self._help_command,
            )
        )

    async def close(self) -> None:
        await self._grok.aclose()
        await super().close()

    async def on_ready(self) -> None:
        if self.user is None:
            return
        logger = logging.getLogger(__name__)
        logger.info("Logged in as %s (id: %s)", self.user, self.user.id)
        logger.info(
            "Guilds joined: %s",
            ", ".join(str(guild.id) for guild in self.guilds) or "(none)",
        )
        if not self._synced:
            logger = logging.getLogger(__name__)
            present_guild_ids = {guild.id for guild in self.guilds}
            for guild_id in self._settings.allowed_guild_ids:
                if guild_id not in present_guild_ids:
                    logger.warning(
                        "Skip sync for guild=%s (bot not in guild)", guild_id
                    )
                    continue
                try:
                    await self.tree.sync(guild=discord.Object(id=guild_id))
                    logger.info("Synced commands for guild=%s", guild_id)
                except discord.Forbidden:
                    logger.warning(
                        "Missing access to sync commands for guild=%s", guild_id
                    )
                except discord.HTTPException:
                    logger.exception("Failed to sync commands for guild=%s", guild_id)
            self._synced = True

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.user is None:
            return

        if message.guild is None:
            return
        if message.guild.id not in self._settings.allowed_guild_ids:
            return

        is_mention = self.user in message.mentions
        logger = logging.getLogger(__name__)
        logger.debug(
            "Message received id=%s author=%s channel=%s guild=%s dm=%s mention=%s",
            message.id,
            message.author.id,
            message.channel.id,
            message.guild.id,
            False,
            is_mention,
        )
        if not is_mention:
            return

        content = message.content
        content = _strip_bot_mention(content, self.user.id)
        content = content.strip()
        logger.debug("Message content length=%s", len(content))

        key = _conversation_key(message)
        lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            if not content:
                content = "（メンションのみ）"

            if _SYNC_PATTERN.match(content):
                try:
                    await self.tree.sync(guild=discord.Object(id=message.guild.id))
                    await message.reply(
                        "スラッシュコマンドを同期しました。", mention_author=False
                    )
                except discord.Forbidden:
                    logger.warning(
                        "Missing access to sync commands for guild=%s",
                        message.guild.id,
                    )
                    await message.reply(
                        "同期に失敗しました。権限を確認してください。",
                        mention_author=False,
                    )
                except discord.HTTPException:
                    logger.exception(
                        "Failed to sync commands for guild=%s", message.guild.id
                    )
                    await message.reply(
                        "同期に失敗しました。しばらくして再試行してください。",
                        mention_author=False,
                    )
                return

            if _HELP_PATTERN.match(content):
                reply = self._help_text()
                await message.reply(reply, mention_author=False)
                await self._log_exchange(
                    message=message,
                    user_content=content,
                    assistant_content=reply,
                )
                preferred_name = await self._get_preferred_name(message)
                call_name = resolve_call_name(
                    user_id=message.author.id,
                    special_user_id=self._settings.special_user_id,
                    display_name=message.author.display_name,
                    preferred_name=preferred_name,
                )
                self._memory.append(
                    key,
                    {
                        "role": "user",
                        "content": self._format_user_message(
                            call_name, message.author.id, content
                        ),
                    },
                )
                self._memory.append(key, {"role": "assistant", "content": reply})
                return

            preferred_name = _extract_preferred_name(content)
            if preferred_name is not None:
                preferred_name = normalize_preferred_name(preferred_name)
                if not preferred_name:
                    reply = "呼び方が空でした。もう一度教えてください。"
                elif (
                    message.author.id != self._settings.special_user_id
                    and is_reserved_name(preferred_name)
                ):
                    reply = "その呼称は使用できません。別の呼び方を指定してください。"
                else:
                    await self._store_preferred_name(message, preferred_name)
                    reply = f"了解しました。これからは「{preferred_name}」と呼びます。"
                await message.reply(reply, mention_author=False)
                await self._log_exchange(
                    message=message,
                    user_content=content,
                    assistant_content=reply,
                )
                self._memory.append(key, {"role": "user", "content": content})
                self._memory.append(key, {"role": "assistant", "content": reply})
                return

            recall_request = _extract_recall_request(content)
            if recall_request is not None:
                content = _strip_recall_command(content)
                if not content:
                    content = "ログを読み取って要点だけ教えてください。"
            history = self._memory.get(key)
            recall_context = await self._maybe_recall_context(
                message, content, recall_request
            )
            preferred_name = await self._get_preferred_name(message)
            call_name = resolve_call_name(
                user_id=message.author.id,
                special_user_id=self._settings.special_user_id,
                display_name=message.author.display_name,
                preferred_name=preferred_name,
            )
            messages = self._build_messages(
                history,
                content,
                recall_context,
                message.author.id,
                call_name,
            )
            try:
                async with message.channel.typing():
                    logger.info(
                        "Calling Grok for user=%s channel=%s guild=%s",
                        message.author.id,
                        message.channel.id,
                        message.guild.id if message.guild else "dm",
                    )
                    reply = await self._grok.chat(
                        messages, user_id=str(message.author.id)
                    )
                logger.info("Grok response received for user=%s", message.author.id)
            except Exception:
                logger.exception("Grok API call failed")
                await message.reply(
                    "API呼び出しに失敗しました。しばらくしてから再試行してください。",
                    mention_author=False,
                )
                return

            await self._log_exchange(
                message=message,
                user_content=content,
                assistant_content=reply,
            )
            self._memory.append(
                key,
                {
                    "role": "user",
                    "content": self._format_user_message(
                        call_name, message.author.id, content
                    ),
                },
            )
            self._memory.append(key, {"role": "assistant", "content": reply})

            for chunk in _chunk_text(reply):
                await message.reply(chunk, mention_author=False)

    async def _help_command(self, interaction: discord.Interaction) -> None:
        if (
            interaction.guild is None
            or interaction.guild.id not in self._settings.allowed_guild_ids
        ):
            return
        await interaction.response.send_message(self._help_text(), ephemeral=True)

    def _help_text(self) -> str:
        auto_keywords = " / ".join(self._settings.auto_recall_keywords)
        lines = [
            "使い方",
            "- メンション: @bot こんにちは",
            "- 呼称指定: @bot 〇〇って呼称してほしい",
            "- 過去ログ: @bot /recall 50 10（末尾50行から10行抽出）",
            f"- 自動リコール: {auto_keywords}",
        ]
        return "\n".join(lines)

    def _build_messages(
        self,
        history: Iterable[ChatMessage],
        content: str,
        recall_context: str | None,
        user_id: int,
        call_name: str,
    ) -> list[ChatMessage]:
        messages: list[ChatMessage] = [
            {"role": "system", "content": self._settings.system_prompt}
        ]
        if recall_context:
            content = f"{recall_context}\n\n{content}"
        messages.extend(history)
        messages.append(
            {
                "role": "user",
                "content": self._format_user_message(call_name, user_id, content),
            }
        )
        return messages

    def _format_user_message(self, call_name: str, user_id: int, content: str) -> str:
        return f"{call_name} (id: {user_id}): {content}"

    async def _maybe_recall_context(
        self,
        message: discord.Message,
        content: str,
        recall_request: tuple[int, int | None] | None,
    ) -> str | None:
        if recall_request is not None:
            lines, pick = recall_request
        else:
            lines = None
            pick = None

        auto_recall = recall_request is None and _has_auto_recall_trigger(
            content, self._settings.auto_recall_keywords
        )
        if recall_request is None and not auto_recall:
            return None

        if lines is None:
            lines = self._settings.auto_recall_lines
        if pick is None:
            pick = self._settings.auto_recall_pick

        entries = await read_user_log_tail(
            self._settings.data_dir,
            message.guild.id if message.guild else None,
            message.author.id,
            lines,
        )
        selected = pick_entries(entries, pick)
        if not selected:
            return None
        block = self._format_recall_entries(selected)
        return f"以下は過去ログの抜粋です。\\n{block}"

    def _format_recall_entries(self, entries: list[dict[str, object]]) -> str:
        lines: list[str] = []
        for entry in entries:
            user_id = entry.get("user_id")
            display_name = entry.get("display_name")
            preferred_name = entry.get("preferred_name")
            role = entry.get("role")
            content = entry.get("content")
            ts = entry.get("ts")

            if not isinstance(user_id, int):
                continue
            if not isinstance(display_name, str):
                display_name = "user"
            preferred_str = preferred_name if isinstance(preferred_name, str) else None
            call_name = resolve_call_name(
                user_id=user_id,
                special_user_id=self._settings.special_user_id,
                display_name=display_name,
                preferred_name=preferred_str,
            )
            lines.append(f"[{ts}] {call_name} ({role}): {content}")
        return "\\n".join(lines)

    async def _log_exchange(
        self, *, message: discord.Message, user_content: str, assistant_content: str
    ) -> None:
        preferred_name = await self._get_preferred_name(message)
        guild_id = message.guild.id if message.guild else None
        user_entry = build_entry(
            guild_id=guild_id,
            channel_id=message.channel.id,
            user_id=message.author.id,
            display_name=message.author.display_name,
            role="user",
            content=user_content,
            message_id=message.id,
            preferred_name=preferred_name,
        )
        await append_logs(self._settings.data_dir, user_entry)
        assistant_entry = build_entry(
            guild_id=guild_id,
            channel_id=message.channel.id,
            user_id=message.author.id,
            display_name=self.user.name if self.user else "bot",
            role="assistant",
            content=assistant_content,
            message_id=None,
            preferred_name=preferred_name,
        )
        await append_logs(self._settings.data_dir, assistant_entry)

    async def _get_preferred_name(self, message: discord.Message) -> str | None:
        meta = await read_user_meta(
            self._settings.data_dir,
            message.guild.id if message.guild else None,
            message.author.id,
        )
        value = meta.get("preferred_name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    async def _store_preferred_name(
        self, message: discord.Message, preferred_name: str
    ) -> None:
        meta = await read_user_meta(
            self._settings.data_dir,
            message.guild.id if message.guild else None,
            message.author.id,
        )
        meta["preferred_name"] = preferred_name
        await write_user_meta(
            self._settings.data_dir,
            message.guild.id if message.guild else None,
            message.author.id,
            meta,
        )
