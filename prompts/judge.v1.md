# Compare the two answers

One answer came from the documentation. The other came from someone who read
the source code and had never seen the documentation. Decide whether the
documentation is right.

## Question

{{question}}

## What the documentation says

{{doc_answer}}

## What the code says

{{response_answer}}

## Evidence for the code answer

{{evidence_blocks}}

## The exact document text

{{raw_text}}

## Verdicts

**correct** — the two answers agree in substance.

Compare meaning, not characters. "30 seconds", "30s" and "thirty seconds" are
the same answer. Extra detail in one is not a disagreement. Different wording
is not a disagreement.

**incorrect** — the documentation states something the code contradicts.

Right value with the wrong unit is incorrect. Right behaviour attributed to
the wrong component is incorrect. A stale name is incorrect.

**unverifiable** — anything else.

Including: the evidence is thin, the difference might be phrasing, the
question turned out to be ambiguous, the code answer is hedged.

## The bar is not symmetric

A wrong `incorrect` means someone edits correct documentation and stops
trusting this system. A wrong `unverifiable` means someone spends thirty
seconds looking.

When you are not clearly confident, `unverifiable`. Do not resolve
uncertainty toward `incorrect` because it feels more useful.

## If incorrect: the replacement

Rewrite `raw_text` so it is accurate, changing as little as possible.

- Keep the surrounding sentence, tone and formatting.
- Change only what the evidence shows is wrong.
- State nothing that is not established by the cited evidence. Not from
  general knowledge, not from what seems likely.
- If you cannot write a correction from the evidence alone, the verdict is
  `unverifiable`, not `incorrect`.

## Output

{{output_schema}}
