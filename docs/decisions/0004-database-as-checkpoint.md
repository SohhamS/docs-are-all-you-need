# 0004. The claim row is the checkpoint, and the commit is pinned

Status: accepted

## Context

Runs need to survive interruption, and stages need to be re-runnable in
isolation during development. Separately, a run reads a repository whose
`main` branch keeps moving.

## Decision

**Every stage writes its output to a column on the claim row.** Status and
stage are columns. Resuming is a query and a re-enqueue. There is no separate
checkpoint store.

**The branch is resolved to a commit SHA once, at run start.** That SHA is
stored on the run and used for every tool call and every `CodeRef`.

## Why the claim row

The table exists anyway for the dashboards. Once stage outputs live on it:

- resume is `SELECT ... WHERE status != 'done'`
- `--from judge` re-runs one stage across a finished run, reusing stored
  investigations
- one row explains a verdict end to end when debugging
- the UI and the pipeline read the same state, so they cannot disagree

The alternative, a framework checkpointer, adds a second persistence mechanism
that the dashboards cannot query, for a capability we already have.

## Why pin the commit

A run over thirty documents takes a while. If someone merges midway, early and
late claims were checked against different code. The run is not reproducible,
two claims about the same function can legitimately disagree, and somebody
loses a day to a bug that is not a bug.

Storing the SHA on every `CodeRef` also lets the authenticity check reject a
citation from a different commit, which catches a stale cached investigation
being reused across runs.

## Consequences

- `update_claim` must write the whole row in one statement. A partial write
  can leave a stage that its stored outputs do not match, and resume then does
  the wrong thing.
- Adding a stage means adding a column, or `--resume --from` silently stops
  working for everything after it.
- The store must be the only source of run state. Nothing else may hold it.
