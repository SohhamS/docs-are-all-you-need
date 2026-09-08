"""Adapter for any endpoint speaking the OpenAI chat-completions shape.

This covers the common cases at once: internal vLLM / TGI / NIM deployments,
OpenAI itself, and most hosted gateways. That is why the router does not
depend on a heavier abstraction layer; the shared wire format already is the
abstraction.

IMPLEMENTATION NOTES
--------------------
- Use `httpx.AsyncClient`, one per provider instance, closed in `close()`.
- Prefer the endpoint's native structured-output support when present
  (`response_format` with a JSON schema, or a grammar parameter). The
  router's reparse loop is the fallback, not the plan.
- Map tool calls into `ToolCall`. Keep provider quirks here; nothing above
  this file should know which vendor answered.
- Retry on connection errors and 5xx with exponential backoff, up to
  `cfg.max_retries`. Do NOT retry on 4xx: a malformed request retried is
  still malformed.
"""

from __future__ import annotations

from typing import Any

from docverify.config import ProviderConfig
from docverify.llm.router import Completion, Provider, ToolSpec


class OpenAICompatProvider(Provider):
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
