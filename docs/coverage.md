# Coverage

## The failure this exists to prevent

A document contains a wrong statement. The classifier never turned it into a
claim. Nothing downstream examined it. The dashboard reports 97% correct.

Nobody can tell, from the dashboard, that a third of the document was never
looked at. A document where twelve of forty assertions were found looks
exactly like a document with twelve assertions. That is the silent failure,
and the first time somebody finds a bad statement in a document this system
marked green, the project loses its credibility.

Coverage is the number that makes that visible.

## How it is computed

Not estimated, and not self-reported by a model. Arithmetic over stored rows.

The segmenter splits a document into units that **tile it completely**: no
gaps, no overlaps, in order. `assert_partition` enforces this. The classifier
then produces one claim row for **every** unit, including the ones that assert
nothing. So every character of the document is accounted for by exactly one
row, and coverage is a sum.

Headings and captions are excluded from the denominator. Counting a table of
contents against your coverage makes every document look worse than it is.

## The two numbers

**Extraction coverage** = claim chars / total content chars

How much of the document was even considered checkable. Low means the
classifier is missing assertions, or the document is genuinely mostly prose.
Those two need different responses, so it is read alongside the claim-type
counts.

**Resolution coverage** = resolved chars / claim chars

How much of the checkable content actually reached a verdict rather than dying
in a failure. Low means the pipeline is breaking, not that the document is
bad.

## Both are always displayed

Verdict counts alone are misleading in a specific and dangerous direction:

```
100% correct  @  30% extraction coverage      verified almost nothing
 94% correct  @  91% extraction coverage      a real result
```

The CLI summary and the dashboard cards must show both, plus the failed and
skipped counts. A summary that shows only verdicts hides exactly the thing
coverage exists to reveal.

## The visualization tab

`build_highlights` returns one segment per unit, tiling the document. The UI
renders the normalized text with every character coloured:

| Colour | Meaning |
|---|---|
| purple | no claim: `NONE` or `NAVIGATIONAL` |
| grey | skipped: `CONCEPTUAL` or `BEHAVIOURAL` |
| green | correct |
| red | incorrect |
| amber | unverifiable |
| outlined | failed |

Coverage read as a picture. A document showing large purple regions where you
expected checkable content is a classifier problem you can see in a second and
would never find in a percentage.

Note this renders the normalized text, not the original PDF or Word layout.
See ADR 0005.
