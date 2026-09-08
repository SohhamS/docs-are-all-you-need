# Data model

`src/docverify/models.py` is authoritative. This is the map.

```
Run ─┬─ code_ref            resolved commit SHA, pinned at run start
     ├─ declared_version    typed in by the operator
     └─ config_snapshot     the effective config this run used

     └── NormalizedDoc ─┬─ text        canonical plain text
                        └─ units[]     tile `text` completely, in order

                            └── Claim (one per unit)
                                 ├─ claim_type   what kind of assertion
                                 ├─ question / doc_answer / raw_text
                                 ├─ stage        where it is
                                 ├─ status       did the machinery work
                                 ├─ investigation      ─┐
                                 ├─ evidence_report     ├ stage outputs,
                                 ├─ judgement          ─┘ each a checkpoint
                                 └─ human_notes[]      append-only
```

## Claim is the unit of work

After classification everything is per-claim. Document status is derived by
aggregation, never stored.

## Status and verdict are different columns

`ClaimStatus` answers *did the machinery work*: pending, running, done,
failed, skipped.

`Verdict` answers *what did we conclude*: correct, incorrect, unverifiable.

A crashed claim is `FAILED` with **no verdict**. Collapsing these puts
infrastructure failures in a technical writer's review queue, and they learn
to ignore the queue.

## Ids are derived from content

```
doc_id    = uuid5(run_id, source_sha256)
unit_id   = uuid5(doc_sha256, ordinal, start, end)
claim_id  = uuid5(doc_sha256, unit_id, normalize(question))
```

Re-ingesting an unchanged document yields the same ids, so nothing duplicates,
resume matches stored outputs, and the ids double as cache keys.

`question_key` exists but is unused in phase 1. Deduplicating investigations
by question is a roadmap item; the key is defined now so adopting it later
needs no migration.

## Stage outputs are the checkpoint

Each stage's output is a column on the claim row, written when that stage
completes. That single fact gives:

- **resume**: select unfinished claims, re-enqueue at their recorded stage
- **stage re-run**: `--from judge` re-judges a finished run reusing every
  stored investigation
- **debuggability**: one row explains a verdict end to end
- **the dashboards**: the same table the UI queries

See ADR 0004 for why this rather than a framework checkpointer.
