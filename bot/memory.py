from __future__ import annotations

from collections import deque
from typing import Deque, Protocol
import logging

from .types import ChatMessage

ConversationKey = tuple[int | None, int]


class MemoryBackend(Protocol):
    def get(self, key: ConversationKey) -> list[ChatMessage]: ...

    def append(self, key: ConversationKey, message: ChatMessage) -> None: ...

    def load_history(
        self, key: ConversationKey, messages: list[ChatMessage]
    ) -> None: ...

    def clear(self, key: ConversationKey) -> None: ...


class InMemoryBackend:
    def __init__(self, max_history: int) -> None:
        self._max_history = max_history
        self._store: dict[ConversationKey, Deque[ChatMessage]] = {}
        self._logger = logging.getLogger(__name__)

    def get(self, key: ConversationKey) -> list[ChatMessage]:
        items = list(self._store.get(key, deque()))
        self._logger.debug("Memory get key=%s size=%s", key, len(items))
        return items

    def append(self, key: ConversationKey, message: ChatMessage) -> None:
        if key not in self._store:
            self._store[key] = deque(maxlen=self._max_history)
        self._store[key].append(message)
        self._logger.debug(
            "Memory append key=%s role=%s size=%s",
            key,
            message["role"],
            len(self._store[key]),
        )

    def load_history(self, key: ConversationKey, messages: list[ChatMessage]) -> None:
        self._store[key] = deque(messages, maxlen=self._max_history)
        self._logger.debug("Memory load key=%s size=%s", key, len(self._store[key]))

    def clear(self, key: ConversationKey) -> None:
        self._store.pop(key, None)
        self._logger.debug("Memory cleared key=%s", key)
