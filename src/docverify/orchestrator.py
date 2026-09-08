"""The orchestrator: a plain loop over a fixed four-step pipeline.

There is no graph framework here, and that is a decision rather than an
omission. See ADR 0001. The short version: the pipeline is a fixed DAG with
per-claim fan-out and exactly one genuinely agentic node. A framework here
would own the control flow and bring a second persistence mechanism whose
tables the dashboards cannot query, and two sources of truth for run state is
a reliable bug generator.

THE WORKER LOOP
---------------
Every worker does the same five things, whatever stage it serves:

    consume a message  ->  load the claim from the store
                       ->  run the stage
                       ->  persist the result
                       ->  publish the next message

The message carries ids only. The claim's state lives in the store, and the
write that persists a stage's output IS the checkpoint. If that write did not
happen, the stage did not happen.

RESUME
------
Because every stage output is a column on the claim row, resuming is a query
and a re-enqueue:

    dv run --resume <run_id>              continue where it stopped
    dv run --resume <run_id> --from judge re-judge a finished run, reusing
                                          every stored investigation

The second is the developer loop that matters. Changing the judge prompt and
re-judging three hundred claims takes minutes and costs nothing, because the
expensive agentic stage is not repeated.

CONCURRENCY
-----------
Per-stage worker counts come from `config.stages.<name>.concurrency`, and the
real throttle is the LLM router's limiter. Sequencing documents is a
throughput knob, not a safety mechanism: the fan-out to parallel claims
happens inside a document, so processing documents one at a time does not
bound peak load at all.
"""

from __future__ import annotations

from docverify.bus import Bus, Message
from docverify.codetools.protocol import CodeTools
from docverify.config import Config
from docverify.llm.router import LLMRouter
from docverify.models import Run, Stage
from docverify.store.protocol import Store


class Orchestrator:
    """Owns run lifecycle, worker loops, retries and resume."""

    def __init__(
        self,
        config: Config,
        store: Store,
        bus: Bus,
        llm: LLMRouter,
        codetools: CodeTools,
    ) -> None:
        self.config = config
        self.store = store
        self.bus = bus
        self.llm = llm
        self.codetools = codetools

    async def start_run(
        self,
        doc_paths: list[str],
        *,
        declared_version: str | None = None,
    ) -> Run:
        """Create a run and process it to completion.

        Order matters at the start:

          1. Resolve `config.codetools.branch` to a commit SHA, ONCE, and
             store it on the run. Every tool call and every CodeRef in this
             run uses that SHA. A run that follows a moving branch can have
             its first and last claims disagree about the same code, and its
             results cannot be reproduced or defended.
          2. Snapshot the effective config onto the run, so the result stays
             explicable after someone edits the config file.
          3. Ingest each document, segment it, persist it.
          4. Classify, which produces the claim rows.
          5. Enqueue every CODE_VERIFIABLE claim at INVESTIGATE and run the
             workers until idle.
        """
        raise NotImplementedError

    async def resume_run(self, run_id: str, *, from_stage: Stage | None = None) -> Run:
        """Resume, or re-run one stage across a finished run.

        With `from_stage`, claims already past that stage are reset to it and
        re-enqueued, reusing their stored earlier outputs. Everything before
        it is left untouched.
        """
        raise NotImplementedError

    async def _worker(self, stage: Stage) -> None:
        """One worker for one stage.

        Contract, and it is the same for every stage:

          - Load the claim by id. Never trust a payload for content: a
            resumed run would then process stale data.
          - Set status RUNNING, persist, run the stage.
          - On success: store the output, advance `stage`, persist, publish
            the next message. Publish AFTER the write; publishing first means
            a crash in between loses the work with no record of it.
          - On StageError: increment `attempts`. Below `max_attempts`, nack
            with requeue and exponential backoff. At the limit, set status
            FAILED with the error text and do not publish.
          - Retrying `investigate` re-samples rather than repeating: it is a
            nondeterministic stage, so a retry gives a different answer, not
            the same answer more reliably. Worth knowing when reading logs.
          - A FAILED claim never receives a verdict. Status and verdict are
            different columns because they are different questions, and a
            crashed claim filed as "unverifiable" puts an infrastructure
            problem in front of a technical writer.
        """
        raise NotImplementedError

    async def _next_stage(self, current: Stage) -> Stage | None:
        """The successor stage, or None when the claim is finished."""
        order = [Stage.CLASSIFY, Stage.INVESTIGATE, Stage.EVIDENCE, Stage.JUDGE]
        i = order.index(current)
        return order[i + 1] if i + 1 < len(order) else None

    async def _publish(self, message: Message) -> None:
        await self.bus.publish(message)
