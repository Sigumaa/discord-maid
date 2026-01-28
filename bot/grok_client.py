from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Any

from xai_sdk import AsyncClient  # type: ignore[import-untyped]
from xai_sdk.chat import assistant, image, system, user  # type: ignore[import-untyped]
from xai_sdk.tools import web_search, x_search  # type: ignore[import-untyped]

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
        self,
        messages: Iterable[ChatMessage],
        *,
        user_id: str | None = None,
        enable_web_search: bool = False,
        enable_x_search: bool = False,
        web_search_allowed_domains: list[str] | None = None,
        web_search_excluded_domains: list[str] | None = None,
        web_search_country: str | None = None,
        image_urls: list[str] | None = None,
        image_detail: str = "auto",
    ) -> str:
        logger = logging.getLogger(__name__)
        await self._ensure_client()
        raw_messages = list(messages)
        chat_messages: list[Any] = []
        if image_urls and raw_messages and raw_messages[-1]["role"] == "user":
            last = raw_messages.pop()
            chat_messages.extend(_to_sdk_message(message) for message in raw_messages)
            parts = [last["content"]]
            for url in image_urls:
                parts.append(image(image_url=url, detail=image_detail))
            chat_messages.append(user(*parts))
        else:
            chat_messages = [_to_sdk_message(message) for message in raw_messages]
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
        tools = None
        include = None
        if enable_web_search or enable_x_search:
            tool_list = []
            allowed = web_search_allowed_domains or None
            excluded = web_search_excluded_domains or None
            if allowed and excluded:
                logger.warning(
                    "Both allowed and excluded domains set; using allowed only"
                )
                excluded = None
            if enable_web_search:
                tool_list.append(
                    web_search(
                        allowed_domains=allowed,
                        excluded_domains=excluded,
                        user_location_country=web_search_country,
                    )
                )
            if enable_x_search:
                tool_list.append(x_search())
            tools = tool_list or None
            include = ["inline_citations"]

        chat = client.chat.create(
            model=self._model,
            messages=chat_messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            user=user_id,
            tools=tools,
            include=include,
            store_messages=False if image_urls else None,
        )
        response = await chat.sample()
        content = response.content
        if not isinstance(content, str):
            raise ValueError("Invalid content in Grok API response")
        if enable_web_search or enable_x_search:
            tool_calls = getattr(response, "tool_calls", None)
            if tool_calls:
                logger.debug("Grok tool_calls=%s", tool_calls)
            citations = getattr(response, "citations", None)
            if isinstance(citations, list) and citations:
                unique = list(dict.fromkeys(str(c) for c in citations))
                sources_text = "\n".join(f"- {c}" for c in unique)
                content = f"{content}\n\n出典:\n{sources_text}"
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
