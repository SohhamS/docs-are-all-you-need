# The pipeline, stage by stage

## 0. Ingest and segment (deterministic)

`ingest/loader.py`, `ingest/segment.py`. No model involved.

Parse to one internal format, hash the source bytes, split into units that
tile the document completely. Offsets originate here and only here.

Scanned PDFs are rejected rather than OCR'd. Claims generated from garbled
text still produce confident-looking verdicts, and nothing on the dashboard
would reveal that the input was noise.

## 1. Classify

`stages/classify.py`. Input: a segmented document. Output: one `Claim` per
unit.

For each unit: what kind of assertion is this, and if it is code-checkable,
what is the question and what does the document answer?

Every unit gets a row. Non-checkable units get status `SKIPPED` and their
`ClaimType`, so the coverage view can colour them.

**The hard requirement.** Every question must be answerable by someone who has
never read the document, because the next stage never will.

    bad:  "What is the default timeout?"
    good: "What is the default value of the request_timeout option on the Go
           client's Config struct?"

`heading_path` and the document title are the raw material. A question that
only makes sense in context produces a confident wrong answer downstream,
which is worse than no answer at all.

## 2. Investigate

`stages/investigate.py`. Input: question plus scoping context. Output: an
answer plus citations.

An agentic loop over the code tools, bounded by `max_tool_calls`.

**Blind to the document.** No `doc_answer`, no `raw_text`. See ADR 0003.

**Citations are selected, never typed.** Refs returned by tool calls are kept
against opaque ids; only the ids are exposed to the model. It cannot fabricate
a citation it is never allowed to spell.

Exhausting the tool budget yields an empty answer, which becomes
`UNVERIFIABLE`. It must never produce a guess. An investigator that cannot say
"I could not determine this" is worse than useless, because its guesses are
indistinguishable from its findings.

## 3. Evidence

`stages/evidence.py`. Two checks, both on every claim.

**Authenticity** (deterministic, implemented): does each citation resolve
exactly at the pinned commit? Path exists, line range valid, snippet hash
matches, ref is the run's SHA, span within limit, at least one citation
present.

**Sufficiency** (semantic): do those citations actually support the answer?

Skipping sufficiency when authenticity passes is the system's worst failure
mode. Authenticity passing means the model did not invent a path. It says
nothing about relevance. See ADR 0003 and `AGENTS.md` invariant 4.

A failed authenticity check is terminal: `UNVERIFIABLE`, reason
`EVIDENCE_NOT_AUTHENTIC`, no model consulted. No reasoning makes a fabricated
citation real.

## 4. Judge

`stages/judge.py`. Input: everything. Output: a verdict, and a patch when the
verdict is `INCORRECT`.

The first three decisions need no model:

1. authenticity failed -> `UNVERIFIABLE` / `EVIDENCE_NOT_AUTHENTIC`
2. sufficiency failed -> `UNVERIFIABLE` / `EVIDENCE_INSUFFICIENT`
3. empty answer -> `UNVERIFIABLE` / `NO_EVIDENCE_FOUND` or
   `TOOL_BUDGET_EXHAUSTED`

Then, semantic comparison. "30 seconds", "30s" and "thirty seconds" are the
same answer. Right value with the wrong unit is `INCORRECT`.

`INCORRECT` clears a higher bar than `CORRECT`. When in doubt, `UNVERIFIABLE`.

The patch is a span replacement carrying `old_text_sha256`, and may only
assert facts present in its cited evidence. It is what actually reaches a
customer's documentation, so it gets the same discipline as the finding.

## 5. Review

Three verdict tabs plus a failed tab, plus the visualization tab.

Dismissing an `INCORRECT` finding requires a `DismissalReason`. One of them is
`CODE_ISSUE_NOT_DOC_ISSUE`, because the product's assumption that the code is
always right is not always true, and a reviewer who hits a genuine bug needs
an honest exit rather than a choice between editing a document to describe the
bug and quietly losing faith in the tool.
