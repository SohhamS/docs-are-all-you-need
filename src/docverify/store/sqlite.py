"""SQLite implementation of `Store`.

SQLite is the phase 1 choice because there is no multi-user access yet. The
schema is deliberately ordinary SQL with JSON columns for the nested stage
outputs, so moving to Postgres later is a driver swap and a migration, not a
redesign.

Schema lives in `migrations/0001_init.sql`. Read it before implementing;
it is the authoritative table shape.

IMPLEMENTATION NOTES
--------------------
- Use `aiosqlite`, or run the stdlib `sqlite3` calls in a thread executor.
  Do not block the event loop; the orchestrator runs many workers.
- Turn on WAL mode (`PRAGMA journal_mode=WAL`) so readers (the API) do not
  block writers (the workers).
- `update_claim` must write the whole row in one statement. Partial updates
  across several statements can leave a claim with a stage that its stored
  outputs do not match, and a resume will then do the wrong thing.
- Serialise nested models with `model_dump_json()` and parse with
  `Model.model_validate_json()`. Do not hand-roll the JSON.
"""

from __future__ import annotations

from pathlib import Path

from docverify.models import (
    Claim,
    ClaimStatus,
    NormalizedDoc,
    Run,
    Stage,
)

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "migrations" / "0001_init.sql"


class SqliteStore:
    """See `docverify.store.protocol.Store` for the contract."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def init(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def create_run(self, run: Run) -> None:
        raise NotImplementedError

    async def get_run(self, run_id: str) -> Run | None:
        raise NotImplementedError

    async def update_run(self, run: Run) -> None:
        raise NotImplementedError

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[Run]:
        raise NotImplementedError

    async def put_doc(self, doc: NormalizedDoc) -> None:
        raise NotImplementedError

    async def get_doc(self, doc_id: str) -> NormalizedDoc | None:
        raise NotImplementedError

    async def list_docs(self, run_id: str) -> list[NormalizedDoc]:
        raise NotImplementedError

    async def put_claims(self, claims: list[Claim]) -> None:
        raise NotImplementedError

    async def get_claim(self, claim_id: str) -> Claim | None:
        raise NotImplementedError

    async def update_claim(self, claim: Claim) -> None:
        raise NotImplementedError

    async def list_claims(
        self,
        run_id: str,
        *,
        doc_id: str | None = None,
        stage: Stage | None = None,
        status: ClaimStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Claim]:
        raise NotImplementedError

    async def unfinished_claims(
        self, run_id: str, *, from_stage: Stage | None = None
    ) -> list[Claim]:
        raise NotImplementedError

    async def append_human_note(self, claim_id: str, note_json: str) -> None:
        raise NotImplementedError
