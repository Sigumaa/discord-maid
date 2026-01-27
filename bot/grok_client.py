from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Any

from xai_sdk import AsyncClient  # type: ignore[import-untyped]
from xai_sdk.chat import assistant, system, user  # type: ignore[import-untyped]

from .types import ChatMessage


class GrokClient:
    def __init__(
        self,
        api_key: str,
        api_host: str,
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._api_key = api_key
        self._api_host = api_host
        self._client: AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def chat(
        self, messages: Iterable[ChatMessage], user_id: str | None = None
    ) -> str:
        logger = logging.getLogger(__name__)
        await self._ensure_client()
        chat_messages = [_to_sdk_message(message) for message in messages]
        client = self._client
        if client is None:
            raise RuntimeError("Grok client was not initialized")
        logger.debug(
            "Grok request model=%s temp=%s max_tokens=%s messages=%s user_id=%s",
            self._model,
            self._temperature,
            self._max_tokens,
            len(chat_messages),
            user_id,
        )
        chat = client.chat.create(
            model=self._model,
            messages=chat_messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            user=user_id,
        )
        response = await chat.sample()
        content = response.content
        if not isinstance(content, str):
            raise ValueError("Invalid content in Grok API response")
        logger.debug("Grok response length=%s", len(content))
        return content.strip()

    async def aclose(self) -> None:
        if self._client is not None:
            self._client.close()

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return
        async with self._client_lock:
            if self._client is None:
                self._client = AsyncClient(
                    api_key=self._api_key, api_host=self._api_host
                )


def _to_sdk_message(message: ChatMessage) -> Any:
    role = message["role"]
    content = message["content"]
    if role == "system":
        return system(content)
    if role == "user":
        return user(content)
    if role == "assistant":
        return assistant(content)
    raise ValueError(f"Unsupported role: {role}")
