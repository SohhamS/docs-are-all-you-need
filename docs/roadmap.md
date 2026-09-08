# Deferred, deliberately

Recorded so nobody has to rediscover the reasoning, and so nobody implements
one of these thinking it was forgotten.

## Deduplicate investigations by question

The same question asked in three documents is investigated three times, and
can get three different answers, because three independent agentic runs take
different paths.

`ids.question_key()` already exists. The change is: look up an investigation
by question key before running one, and store investigations in their own
table with a many-to-one relationship to claims.

Buys consistency and a large cost saving. Deferred because it complicates the
claim row's ownership of its stage outputs, and phase 1 needs that simplicity
more than it needs the saving.

## Self-consistency sampling

`InvestigateConfig.samples` above 1: run the investigator N times, take the
answer with citation agreement, treat disagreement as an `UNVERIFIABLE`
signal.

This is the only calibrated confidence measure available. A model's stated
confidence in its own answer is not one.

Deferred until a labelled set exists, because without one there is no way to
tell whether it helps.

## Send a claim back to the investigator with a human hint

A reviewer looking at an `UNVERIFIABLE` claim often knows where to look. The
state machine already supports moving a claim back to an earlier stage; what
is missing is the note plumbing and the UI.

Deferred to phase 2 by decision, not oversight.

## Sandboxed execution of code samples

Documents contain code samples. Running them in a sandbox would settle
`BEHAVIOURAL` claims that reading code cannot.

Phase 2, with its own security review. Phase 1 executes nothing.

## Comparing runs across releases

Documents are per-run inputs today. Re-validating the same document against a
later release and diffing the verdicts would show which parts of the
documentation a release broke.

Needs documents to become first-class entities with versions. A schema change,
not a redesign.

## Original-layout rendering

The visualization tab renders normalized text. Overlaying highlights on the
original PDF or Word layout needs text-layer coordinate work. Nobody has asked
for it.

## OCR for scanned PDFs

Currently rejected at ingest. If OCR is added, mark the document as
OCR-derived and surface that on every claim from it, so a reviewer knows the
input was reconstructed.

## Postgres, Redis, Kubernetes, auth

Not phase 1. The seams exist. `SKILLS.md` has the steps. Do not pre-build
them.
