"""The LLM seam: provider routing, throttling, schema enforcement, tracing.

Three jobs, all of them cross-cutting, all of them done once here so that no
stage has to think about them:

1. ROUTING. Stages ask for a provider by name; the router resolves it. That
   is what makes "plug in an internal endpoint, or an OpenAI-spec one, or
   Gemini" a config change.

2. THROTTLING. The global limiter lives here, because this is where the
   constrained resource actually is. Sequencing documents does not bound LLM
   load: the fan-out to parallel claims happens inside a document.

3. SCHEMA ENFORCEMENT. `complete_json` validates against a pydantic model and
   retries a bounded number of times on malformed output. Quantised models
   produce invalid JSON considerably more often than they reason badly, and
   every stage would otherwise reimplement this badly.

Tracing wraps the client rather than each stage, so every call is traced with
run/doc/claim ids attached and no stage carries tracing code.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from docverify.config import LimiterConfig, LLMConfig, ProviderConfig

T = TypeVar("T", bound=BaseModel)


class ToolSpec(BaseModel):
    """A tool offered to a model, in the usual JSON-schema function shape."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class Completion(BaseModel):
    """One model response."""

    text: str = ""
    tool_calls: list[ToolCall] = []
    model_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""


class Provider:
    """Base class for endpoint adapters. See `providers/`."""

    def __init__(self, name: str, cfg: ProviderConfig) -> None:
        self.name = name
        self.cfg = cfg

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
        return None


class RateLimiter:
    """Concurrency cap plus a token bucket, together.

    Concurrency alone lets a burst of short calls hammer an endpoint; rate
    alone lets long calls pile up. Both are needed.
    """

    def __init__(self, cfg: LimiterConfig) -> None:
        self._sem = asyncio.Semaphore(cfg.max_in_flight)
        self._rps = cfg.requests_per_second
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    async def __aenter__(self) -> None:
        await self._sem.acquire()
        async with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next_slot - now)
            self._next_slot = max(now, self._next_slot) + (1.0 / self._rps)
        if wait:
            await asyncio.sleep(wait)

    async def __aexit__(self, *exc: object) -> None:
        self._sem.release()


class SchemaValidationError(RuntimeError):
    """Raised when a model could not produce output matching the schema after
    the configured number of retries. Callers should surface this as a FAILED
    claim, never as a verdict."""


class LLMRouter:
    """The only thing in the codebase that talks to a model."""

    def __init__(self, cfg: LLMConfig, tracer: Any | None = None) -> None:
        self.cfg = cfg
        self.limiter = RateLimiter(cfg.limiter)
        self.tracer = tracer
        self._providers: dict[str, Provider] = {}

    def provider(self, name: str | None = None) -> Provider:
        """Resolve a provider by name, building it on first use."""
        raise NotImplementedError

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        provider: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout_s: float | None = None,
        trace: dict[str, str] | None = None,
    ) -> Completion:
        """A single completion, throttled and traced.

        `trace` carries run_id / doc_id / claim_id / stage so the Langfuse
        span can be found later. It must never be required for correctness:
        the application has to run with tracing disabled.
        """
        raise NotImplementedError

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        model: type[T],
        *,
        provider: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout_s: float | None = None,
        trace: dict[str, str] | None = None,
    ) -> T:
        """Complete and validate against `model`.

        On a validation failure, retry up to `ProviderConfig.schema_retries`
        times, appending the validation error to the conversation so the model
        can correct itself. Raise `SchemaValidationError` if it never does.

        Use the endpoint's native constrained decoding or JSON-schema mode
        when it has one; the retry loop is the fallback, not the plan.
        """
        raise NotImplementedError

    async def close(self) -> None:
        for p in self._providers.values():
            await p.close()
