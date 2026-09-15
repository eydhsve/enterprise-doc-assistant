"""Bounded multi-turn conversation memory."""

from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any


class ConversationMemory:
    """Keep recent user/assistant messages under a fixed message budget."""

    def __init__(
        self,
        max_messages: int = 12,
        max_context_chars: int = 14000,
    ) -> None:
        if max_messages < 2:
            raise ValueError("max_messages 不能小于 2。")
        if max_context_chars < 1000:
            raise ValueError("max_context_chars 不能小于 1000。")

        self.max_messages = max_messages
        self.max_context_chars = max_context_chars
        self._messages: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        """Append one completed user/assistant turn and trim old turns."""

        user_content = (user_message or "").strip()
        assistant_content = (assistant_message or "").strip()
        if not user_content:
            return
        if not assistant_content:
            assistant_content = "本轮未生成有效回答。"

        with self._lock:
            self._messages.extend(
                [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ]
            )
            self._trim()

    def add_message(self, role: str, content: str) -> None:
        """Append a single role message. Primarily useful for tests."""

        if role not in {"user", "assistant"}:
            raise ValueError("ConversationMemory 仅保存 user 或 assistant 消息。")
        text = (content or "").strip()
        if not text:
            return
        with self._lock:
            self._messages.append({"role": role, "content": text})
            self._trim()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._messages)

    def context_messages(
        self,
        system_prompt: str,
        current_user_message: str | None = None,
    ) -> list[dict[str, str]]:
        """Build a size-bounded OpenAI-style context."""

        with self._lock:
            history = deepcopy(self._messages)

        selected: list[dict[str, str]] = []
        remaining = max(0, self.max_context_chars - len(system_prompt))
        current_content = (current_user_message or "").strip()

        if current_content:
            current_budget = min(remaining, max(500, remaining // 2))
            current_content = (
                current_content[:current_budget] if current_budget > 0 else ""
            )
            remaining -= len(current_content)

        for message in reversed(history):
            content = str(message.get("content", ""))
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[-remaining:]
            selected.append(
                {
                    "role": str(message.get("role", "user")),
                    "content": content,
                }
            )
            remaining -= len(content)

        selected.reverse()
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(selected)

        if current_content:
            messages.append({"role": "user", "content": current_content})
        return messages

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._messages)

    def _trim(self) -> None:
        while len(self._messages) > self.max_messages:
            self._messages.pop(0)

        # A history should start with a user message, not an orphan assistant reply.
        while self._messages and self._messages[0]["role"] != "user":
            self._messages.pop(0)
