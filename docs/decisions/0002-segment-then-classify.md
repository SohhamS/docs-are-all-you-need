# 0002. Segment deterministically, then classify

Status: accepted

## Context

The original design was "an LLM reads the document and extracts
(question, doc_answer, raw_text) tuples". The product requires a view of the
whole document with every span coloured by outcome, and a coverage number per
document and per run.

## Decision

Two passes.

**Pass 1, deterministic.** Split the document into atomic units by structure
and sentence boundaries. Each unit gets an id and exact character offsets. No
model.

**Pass 2, the model.** For each unit: what kind of assertion is this, and if
code-checkable, what is the question and the document's answer? The model
receives unit ids and returns unit ids.

Every unit gets a claim row, including the ones asserting nothing.

## Why

**Coverage becomes arithmetic.** "Extract the claims" cannot report what it
missed. A document where twelve of forty assertions were found looks identical
to a document with twelve. With a complete partition, coverage is a sum over
rows and the missing third is visible.

**Atomicity becomes structural.** Asking a model to "be atomic" over a whole
document does not produce atomicity. Splitting first reduces the problem from
"decompose a document" to "decompose one sentence".

**Offsets stay exact.** Models are unreliable at character arithmetic. The
highlighting view depends on offsets being right, and the splitter produces
them for free.

**The classification task is easier than the extraction task.** "Find all the
claims in this document" is open-ended and requires exhaustiveness. "Is this
one sentence a checkable claim" is closed and short-context. This mattered
more when small models were expected; it still holds.

## Consequences

- `segment()` must guarantee the tiling property, and `assert_partition`
  enforces it on every call.
- The classify stage sends batches of units and must reject a response that
  omits units or invents ids, rather than silently dropping them.
- More claim rows than there are real claims. The `SKIPPED` status and the
  `ClaimType` enum carry the difference.
- Sentence splitting quality now matters. It must not break on "e.g.",
  "v1.2.3" or a decimal.
