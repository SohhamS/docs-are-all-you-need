"""Coverage arithmetic and the highlighting payload.

Fully implemented and pure: it takes stored claims and a segmented document
and computes numbers. There is no estimation and no model involved. That is
the whole point. Coverage that a model reports about itself is not coverage.

Read `docs/coverage.md` for what the two ratios mean and why both must be
displayed.
"""

from __future__ import annotations

from collections import Counter

from docverify.models import (
    Claim,
    ClaimStatus,
    ClaimType,
    DocCoverage,
    DocHighlights,
    HighlightSegment,
    NormalizedDoc,
    RunCoverage,
    Verdict,
)

# Units of these kinds carry no verifiable content and are excluded from the
# coverage denominator. Counting a table of contents against your coverage
# would make every document look worse than it is.
NON_CONTENT_KINDS = frozenset({"heading", "caption"})

# A claim counts as "resolved" when the pipeline reached a conclusion about
# it. FAILED does not count: an infrastructure failure is not a verdict.
RESOLVED_STATUSES = frozenset({ClaimStatus.DONE})


def compute_doc_coverage(doc: NormalizedDoc, claims: list[Claim]) -> DocCoverage:
    """Coverage for one document, from its units and its claim rows."""
    by_unit: dict[str, Claim] = {c.unit_id: c for c in claims}

    total_units = 0
    total_chars = 0
    claim_units = 0
    claim_chars = 0
    resolved_units = 0
    resolved_chars = 0

    type_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    for unit in doc.units:
        if unit.kind in NON_CONTENT_KINDS:
            continue
        total_units += 1
        total_chars += unit.span.length

        claim = by_unit.get(unit.id)
        if claim is None:
            # No claim row at all. Treated as unclassified content, which is
            # a coverage gap and must not be silently ignored.
            type_counts[ClaimType.NONE.value] += 1
            continue

        type_counts[claim.claim_type.value] += 1
        status_counts[claim.status.value] += 1
        if claim.verdict is not None:
            verdict_counts[claim.verdict.value] += 1

        if claim.claim_type is not ClaimType.CODE_VERIFIABLE:
            continue

        claim_units += 1
        claim_chars += unit.span.length
        if claim.status in RESOLVED_STATUSES:
            resolved_units += 1
            resolved_chars += unit.span.length

    return DocCoverage(
        doc_id=doc.id,
        total_units=total_units,
        total_chars=total_chars,
        claim_units=claim_units,
        claim_chars=claim_chars,
        resolved_units=resolved_units,
        resolved_chars=resolved_chars,
        counts_by_claim_type=dict(type_counts),
        counts_by_verdict=dict(verdict_counts),
        counts_by_status=dict(status_counts),
    )


def compute_run_coverage(run_id: str, per_doc: list[DocCoverage]) -> RunCoverage:
    """Aggregate document coverage across a run."""
    verdicts: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for d in per_doc:
        verdicts.update(d.counts_by_verdict)
        statuses.update(d.counts_by_status)

    return RunCoverage(
        run_id=run_id,
        per_doc=per_doc,
        total_chars=sum(d.total_chars for d in per_doc),
        claim_chars=sum(d.claim_chars for d in per_doc),
        resolved_chars=sum(d.resolved_chars for d in per_doc),
        counts_by_verdict=dict(verdicts),
        counts_by_status=dict(statuses),
    )


def build_highlights(doc: NormalizedDoc, claims: list[Claim]) -> DocHighlights:
    """Build the payload for the visualization tab.

    Returns one segment per unit, in document order, so the UI can render the
    whole text with every character coloured. Suggested palette, defined in
    the UI rather than here:

        no claim (ClaimType.NONE / NAVIGATIONAL) .... purple
        skipped (CONCEPTUAL / BEHAVIOURAL) .......... grey
        correct ..................................... green
        incorrect ................................... red
        unverifiable ................................ amber
        failed ...................................... hatched / outlined
    """
    by_unit: dict[str, Claim] = {c.unit_id: c for c in claims}
    segments: list[HighlightSegment] = []

    for unit in doc.units:
        claim = by_unit.get(unit.id)
        segments.append(
            HighlightSegment(
                span=unit.span,
                unit_id=unit.id,
                claim_id=claim.id if claim else None,
                claim_type=claim.claim_type if claim else ClaimType.NONE,
                status=claim.status if claim else ClaimStatus.SKIPPED,
                verdict=claim.verdict if claim else None,
            )
        )

    return DocHighlights(
        doc_id=doc.id,
        text=doc.text,
        segments=segments,
        coverage=compute_doc_coverage(doc, claims),
    )


def verdict_totals(claims: list[Claim]) -> dict[Verdict, int]:
    """Counts for the three dashboard tabs."""
    counts = {v: 0 for v in Verdict}
    for c in claims:
        if c.verdict is not None:
            counts[c.verdict] += 1
    return counts
