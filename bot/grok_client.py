from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Iterable

from xai_sdk import AsyncClient  # type: ignore[import-untyped]
from xai_sdk.chat import assistant, image, system, user  # type: ignore[import-untyped]
from xai_sdk.tools import code_execution, web_search, x_search  # type: ignore[import-untyped]

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
        enable_code_execution: bool = False,
        web_search_allowed_domains: list[str] | None = None,
        web_search_excluded_domains: list[str] | None = None,
        web_search_country: str | None = None,
        image_urls: list[str] | None = None,
        image_detail: str = "auto",
    ) -> str:
        result = await self.chat_with_meta(
            messages,
            user_id=user_id,
            enable_web_search=enable_web_search,
            enable_x_search=enable_x_search,
            enable_code_execution=enable_code_execution,
            web_search_allowed_domains=web_search_allowed_domains,
            web_search_excluded_domains=web_search_excluded_domains,
            web_search_country=web_search_country,
            image_urls=image_urls,
            image_detail=image_detail,
        )
        return result.content

    async def chat_with_meta(
        self,
        messages: Iterable[ChatMessage],
        *,
        user_id: str | None = None,
        enable_web_search: bool = False,
        enable_x_search: bool = False,
        enable_code_execution: bool = False,
        web_search_allowed_domains: list[str] | None = None,
        web_search_excluded_domains: list[str] | None = None,
        web_search_country: str | None = None,
        image_urls: list[str] | None = None,
        image_detail: str = "auto",
    ) -> ChatResult:
        content, tool_calls, citations = await self._run_chat(
            messages,
            user_id=user_id,
            enable_web_search=enable_web_search,
            enable_x_search=enable_x_search,
            enable_code_execution=enable_code_execution,
            web_search_allowed_domains=web_search_allowed_domains,
            web_search_excluded_domains=web_search_excluded_domains,
            web_search_country=web_search_country,
            image_urls=image_urls,
            image_detail=image_detail,
        )
        return ChatResult(
            content=content,
            tool_calls=tool_calls,
            citations=citations,
        )

    async def _run_chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        user_id: str | None,
        enable_web_search: bool,
        enable_x_search: bool,
        enable_code_execution: bool,
        web_search_allowed_domains: list[str] | None,
        web_search_excluded_domains: list[str] | None,
        web_search_country: str | None,
        image_urls: list[str] | None,
        image_detail: str,
    ) -> tuple[str, list[Any] | None, list[Any] | None]:
        logger = logging.getLogger(__name__)
        await self._ensure_client()
        chat_messages = _build_chat_messages(messages, image_urls, image_detail)
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
        tools, include = _assemble_tools(
            enable_web_search=enable_web_search,
            enable_x_search=enable_x_search,
            enable_code_execution=enable_code_execution,
            web_search_allowed_domains=web_search_allowed_domains,
            web_search_excluded_domains=web_search_excluded_domains,
            web_search_country=web_search_country,
        )
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
        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            logger.debug("Grok tool_calls=%s", tool_calls)
        citations = getattr(response, "citations", None)
        content = _format_response_content(
            content,
            citations,
            enable_web_search or enable_x_search,
        )
        logger.debug("Grok response length=%s", len(content))
        return content, tool_calls, citations

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


@dataclass(frozen=True)
class ChatResult:
    content: str
    tool_calls: list[Any] | None
    citations: list[Any] | None


def _build_chat_messages(
    messages: Iterable[ChatMessage],
    image_urls: list[str] | None,
    image_detail: str,
) -> list[Any]:
    raw_messages = list(messages)
    chat_messages: list[Any] = []
    if image_urls and raw_messages and raw_messages[-1]["role"] == "user":
        last = raw_messages.pop()
        chat_messages.extend(_to_sdk_message(message) for message in raw_messages)
        parts = [last["content"]]
        for url in image_urls:
            parts.append(image(image_url=url, detail=image_detail))
        chat_messages.append(user(*parts))
        return chat_messages
    return [_to_sdk_message(message) for message in raw_messages]


def _format_response_content(
    content: str,
    citations: list[Any] | None,
    include_citations: bool,
) -> str:
    if include_citations and isinstance(citations, list) and citations:
        unique = list(dict.fromkeys(str(c) for c in citations))
        sources_text = "\n".join(f"- {c}" for c in unique)
        content = f"{content}\n\n出典:\n{sources_text}"
    return content.strip()


def _assemble_tools(
    *,
    enable_web_search: bool,
    enable_x_search: bool,
    enable_code_execution: bool,
    web_search_allowed_domains: list[str] | None,
    web_search_excluded_domains: list[str] | None,
    web_search_country: str | None,
) -> tuple[list[Any] | None, list[str] | None]:
    tool_list: list[Any] = []
    include: list[str] | None = None
    if enable_web_search:
        allowed = web_search_allowed_domains or None
        excluded = web_search_excluded_domains or None
        if allowed and excluded:
            logger = logging.getLogger(__name__)
            logger.warning("Both allowed and excluded domains set; using allowed only")
            excluded = None
        tool_list.append(
            web_search(
                allowed_domains=allowed,
                excluded_domains=excluded,
                user_location_country=web_search_country,
            )
        )
        include = ["inline_citations"]
    if enable_x_search:
        tool_list.append(x_search())
        include = ["inline_citations"]
    if enable_code_execution:
        tool_list.append(code_execution())
    tools = tool_list or None
    return tools, include


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
