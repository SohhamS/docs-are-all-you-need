"""Adapter for Gemini.

Only needed if Gemini is used directly rather than through an
OpenAI-compatible gateway. If a gateway is available, prefer
`openai_compat` and delete this file rather than maintaining two paths.
"""

from __future__ import annotations

from typing import Any

from docverify.config import ProviderConfig
from docverify.llm.router import Completion, Provider, ToolSpec


class GeminiProvider(Provider):
    def __init__(self, name: str, cfg: ProviderConfig) -> None:
        super().__init__(name, cfg)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        json_schema: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> Completion:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
