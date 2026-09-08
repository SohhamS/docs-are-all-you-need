"""A scripted provider for tests and offline development.

Fully implemented. Every test in this repository runs against this, so the
suite needs no network, no API key and no inference endpoint. If a test
requires a real model to pass, it is testing the model rather than the code.

Usage::

    provider = FakeProvider("fake", cfg, responses=[
        Completion(text='{"claim_type": "code_verifiable", ...}'),
    ])

Responses are returned in order; running out raises, which makes an
unexpected extra model call a loud test failure rather than a silent one.
"""

from __future__ import annotations

from typing import Any

from docverify.config import ProviderConfig
from docverify.llm.router import Completion, Provider, ToolSpec


class FakeProvider(Provider):
    def __init__(
        self,
        name: str,
        cfg: ProviderConfig,
        responses: list[Completion] | None = None,
    ) -> None:
        super().__init__(name, cfg)
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append(
            {
                "messages": messages,
                "tools": [t.name for t in (tools or [])],
                "temperature": temperature,
                "json_schema": json_schema,
            }
        )
        if not self.responses:
            raise AssertionError(
                f"FakeProvider {self.name!r} ran out of scripted responses "
                f"after {len(self.calls)} call(s)"
            )
        return self.responses.pop(0)

    async def close(self) -> None:
        return None
