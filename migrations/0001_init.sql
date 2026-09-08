-- docverify schema, phase 1 (SQLite).
--
-- Design notes worth reading before changing anything here:
--
-- 1. `claims` is both the work queue and the checkpoint. Every stage's output
--    is a JSON column on this row. Resuming a run is a SELECT over it, and
--    re-running one stage across a finished run is a SELECT plus a re-enqueue.
--    Do not move run state into a framework's own checkpoint tables: the UI
--    reads this table, and two sources of truth for run state is a bug
--    generator. See docs/decisions/0004-database-as-checkpoint.md
--
-- 2. `status` and `verdict` are separate columns and mean different things.
--    status = did the machinery work. verdict = what did we conclude.
--    A crashed claim is FAILED with no verdict; it is not "unverifiable".
--
-- 3. `runs.code_ref` is a commit SHA, never a branch name.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    id                TEXT PRIMARY KEY,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    status            TEXT NOT NULL,
    code_repo         TEXT NOT NULL,
    code_ref          TEXT NOT NULL,   -- resolved commit SHA, pinned at run start
    declared_version  TEXT,            -- product version, typed in by the operator
    config_snapshot   TEXT NOT NULL,   -- JSON
    error             TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    source_filename TEXT NOT NULL,
    source_format   TEXT NOT NULL,
    source_sha256   TEXT NOT NULL,
    title           TEXT,
    text            TEXT NOT NULL,     -- canonical plain text; all spans index into this
    units           TEXT NOT NULL,     -- JSON array of Unit; stored, never recomputed
    meta            TEXT NOT NULL      -- JSON
);

CREATE INDEX IF NOT EXISTS idx_documents_run ON documents(run_id);

CREATE TABLE IF NOT EXISTS claims (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    doc_id           TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    unit_id          TEXT NOT NULL,

    claim_type       TEXT NOT NULL,
    question         TEXT NOT NULL DEFAULT '',
    doc_answer       TEXT NOT NULL DEFAULT '',
    raw_text         TEXT NOT NULL DEFAULT '',

    stage            TEXT NOT NULL,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    error            TEXT,

    -- Stage outputs. Each is written once, when that stage completes.
    -- Their presence is what allows a later stage to be re-run alone.
    investigation    TEXT,             -- JSON Investigation
    evidence_report  TEXT,             -- JSON EvidenceReport
    judgement        TEXT,             -- JSON Judgement
    human_notes      TEXT NOT NULL DEFAULT '[]',  -- JSON array, append-only

    -- Denormalised from judgement for cheap dashboard queries. Kept in sync
    -- by update_claim; never written independently.
    verdict          TEXT,

    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_run           ON claims(run_id);
CREATE INDEX IF NOT EXISTS idx_claims_run_verdict   ON claims(run_id, verdict);
CREATE INDEX IF NOT EXISTS idx_claims_run_status    ON claims(run_id, status);
CREATE INDEX IF NOT EXISTS idx_claims_doc           ON claims(doc_id);
CREATE INDEX IF NOT EXISTS idx_claims_resume        ON claims(run_id, status, stage);
CREATE INDEX IF NOT EXISTS idx_claims_unit          ON claims(doc_id, unit_id);
