"""The persistence seam.

The store holds run state and results. It is the ONLY source of truth the UI
reads, and it is also the checkpoint that makes `--resume` work. See ADR 0004.

Only `store/`, `bus.py` and `orchestrator.py` may know that a database
exists. Stages take objects and return objects.
"""

from __future__ import annotations

from typing import Protocol

from docverify.models import (
    Claim,
    ClaimStatus,
    NormalizedDoc,
    Run,
    Stage,
)


class Store(Protocol):
    """Everything the pipeline and the UI need to persist or read back.

    Implementations must be safe to call from multiple concurrent workers.
    """

    async def init(self) -> None:
        """Create schema if absent. Idempotent."""
        ...

    async def close(self) -> None: ...

    # -- runs ---------------------------------------------------------------

    async def create_run(self, run: Run) -> None: ...

    async def get_run(self, run_id: str) -> Run | None: ...

    async def update_run(self, run: Run) -> None: ...

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[Run]: ...

    # -- documents ----------------------------------------------------------

    async def put_doc(self, doc: NormalizedDoc) -> None:
        """Store the normalized document including its units.

        The units must be stored, not recomputed later: coverage and
        highlighting both depend on the exact segmentation the run used, and a
        segmenter change must not silently rewrite an old run's numbers.
        """
        ...

    async def get_doc(self, doc_id: str) -> NormalizedDoc | None: ...

    async def list_docs(self, run_id: str) -> list[NormalizedDoc]: ...

    # -- claims -------------------------------------------------------------

    async def put_claims(self, claims: list[Claim]) -> None:
        """Insert or replace claims by id. Must be idempotent.

        Claim ids are content-derived, so re-classifying an unchanged document
        must overwrite rather than duplicate.
        """
        ...

    async def get_claim(self, claim_id: str) -> Claim | None: ...

    async def update_claim(self, claim: Claim) -> None:
        """Persist a claim after a stage completed.

        Called once per stage transition. This write IS the checkpoint; if it
        did not happen, the stage did not happen.
        """
        ...

    async def list_claims(
        self,
        run_id: str,
        *,
        doc_id: str | None = None,
        stage: Stage | None = None,
        status: ClaimStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Claim]: ...

    async def unfinished_claims(
        self, run_id: str, *, from_stage: Stage | None = None
    ) -> list[Claim]:
        """Claims that need work, for resuming a run.

        With `from_stage` set, also returns claims already DONE at or after
        that stage so they can be re-run against their stored inputs. That is
        what makes `dv run --resume <id> --from judge` re-judge a finished run
        without repeating the expensive investigate stage.
        """
        ...

    async def append_human_note(self, claim_id: str, note_json: str) -> None:
        """Append a reviewer action. Append-only; notes are never edited."""
        ...
