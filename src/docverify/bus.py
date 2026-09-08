"""The transport seam.

A message is a wake-up call carrying an id, not the work item itself. The
claim's actual state lives in the store. That distinction is what lets you
swap `InMemoryBus` for a Redis or SQS implementation later by adding one
class and changing one config value, and it is what keeps the dashboards
queryable while a run is in flight.

Phase 1 ships only `InMemoryBus`, and that is deliberate: an in-process
`asyncio.Queue` behind this interface costs nothing and buys the same
portability that building a broker on day one would.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from pydantic import BaseModel

from docverify.models import Stage


class Message(BaseModel):
    """A unit of work to wake up on.

    Carries ids only. Never carries claim content: if a worker read the
    payload instead of the store, a resumed run would process stale data.
    """

    run_id: str
    doc_id: str
    claim_id: str
    stage: Stage
    attempt: int = 0


class Bus(Protocol):
    """Publish/consume with explicit acknowledgement."""

    async def publish(self, message: Message) -> None: ...

    async def consume(self, stage: Stage) -> Message | None:
        """Take the next message for a stage, or None when draining and empty."""
        ...

    async def ack(self, message: Message) -> None: ...

    async def nack(self, message: Message, *, requeue: bool = True) -> None: ...

    async def close(self) -> None: ...

    @property
    def in_flight(self) -> int:
        """Messages taken but not yet acked. The orchestrator uses this plus
        empty queues to decide a run has finished."""
        ...


class InMemoryBus:
    """An `asyncio.Queue` per stage. Phase 1 default.

    Not durable: if the process dies, queued messages are lost. That is fine,
    because the claim rows are durable and `--resume` rebuilds the queues from
    them. Durability belongs in the store, not the transport.
    """

    def __init__(self, max_queue_size: int = 10_000) -> None:
        self._queues: dict[Stage, asyncio.Queue[Message]] = {
            stage: asyncio.Queue(maxsize=max_queue_size) for stage in Stage
        }
        self._in_flight = 0
        self._draining = False

    async def publish(self, message: Message) -> None:
        await self._queues[message.stage].put(message)

    async def consume(self, stage: Stage) -> Message | None:
        queue = self._queues[stage]
        while True:
            try:
                message = queue.get_nowait()
            except asyncio.QueueEmpty:
                if self._draining:
                    return None
                await asyncio.sleep(0.05)
                continue
            self._in_flight += 1
            return message

    async def ack(self, message: Message) -> None:
        self._in_flight = max(0, self._in_flight - 1)
        self._queues[message.stage].task_done()

    async def nack(self, message: Message, *, requeue: bool = True) -> None:
        self._in_flight = max(0, self._in_flight - 1)
        self._queues[message.stage].task_done()
        if requeue:
            await self.publish(message.model_copy(update={"attempt": message.attempt + 1}))

    async def close(self) -> None:
        self._draining = True

    def start_drain(self) -> None:
        """Tell consumers to return None once their queue empties."""
        self._draining = True

    @property
    def in_flight(self) -> int:
        return self._in_flight

    @property
    def is_idle(self) -> bool:
        return self._in_flight == 0 and all(q.empty() for q in self._queues.values())


def build_bus(kind: str, max_queue_size: int = 10_000) -> Bus:
    """Factory. Add new transports here and nowhere else."""
    if kind == "inmemory":
        return InMemoryBus(max_queue_size=max_queue_size)
    raise ValueError(f"unknown bus kind: {kind!r}")
