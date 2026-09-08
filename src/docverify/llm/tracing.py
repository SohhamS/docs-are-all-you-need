"""Langfuse tracing. Optional, and a no-op when unconfigured.

THE BOUNDARY, and it is worth keeping sharp:

    the store  ->  state and results. Claims, verdicts, evidence, coverage,
                   human notes. Everything the UI queries or a human acts on.

    Langfuse   ->  traces and reasoning. Why the agent did what it did, tool
                   call sequences, token counts, latency.

Nothing the product depends on may live only in a trace. If the UI needs it,
it goes in the store.

The application must run correctly with Langfuse switched off, so every
method here degrades to doing nothing. Tests never require a Langfuse
instance.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any


class NoopSpan:
    def update(self, **kwargs: Any) -> None:
        return None

    def __enter__(self) -> NoopSpan:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    @property
    def trace_id(self) -> str | None:
        return None


class Tracer:
    """Thin wrapper. Returns `NoopSpan` when disabled."""

    def __init__(self, enabled: bool = False, client: Any | None = None) -> None:
        self.enabled = enabled
        self.client = client

    def span(self, name: str, **attrs: Any) -> Any:
        """Start a span. `attrs` should always include run_id, and doc_id and
        claim_id when known, so a trace can be located from a dashboard row."""
        if not self.enabled or self.client is None:
            return NoopSpan()
        raise NotImplementedError

    def flush(self) -> None:
        if self.enabled and self.client is not None:
            raise NotImplementedError


def build_tracer(enabled: bool) -> Tracer:
    """Build a tracer, falling back to a no-op if Langfuse is unavailable.

    A missing tracing dependency must never stop a run. Degrade, log once,
    carry on.
    """
    if not enabled:
        return Tracer(enabled=False)
    raise NotImplementedError
