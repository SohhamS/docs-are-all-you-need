"""Coverage arithmetic.

These tests exist because coverage is the number that reveals the system's
silent failure: a document where most assertions were never extracted looking
identical to one that passed. If this arithmetic is wrong, that failure
becomes invisible again.
"""

from __future__ import annotations

from docverify.coverage import build_highlights, compute_doc_coverage, compute_run_coverage
from docverify.models import ClaimStatus, ClaimType, NormalizedDoc, Verdict
from tests.conftest import make_claim


def test_units_tile_the_document(sample_doc: NormalizedDoc) -> None:
    """The property every coverage number depends on."""
    units = sample_doc.units
    assert units[0].span.start == 0
    assert units[-1].span.end == len(sample_doc.text)
    for a, b in zip(units[:-1], units[1:], strict=True):
        assert a.span.end == b.span.start


def test_headings_are_excluded_from_the_denominator(sample_doc: NormalizedDoc) -> None:
    """Counting a heading against coverage makes every document look worse."""
    cov = compute_doc_coverage(sample_doc, [])
    heading = sample_doc.units[0]
    assert cov.total_chars == len(sample_doc.text) - heading.span.length
    assert cov.total_units == len(sample_doc.units) - 1


def test_extraction_and_resolution_are_different_numbers(sample_doc: NormalizedDoc) -> None:
    """Two checkable claims, one resolved. Both ratios must reflect that."""
    _, a, b, c = sample_doc.units
    claims = [
        make_claim(a, ClaimType.CODE_VERIFIABLE, ClaimStatus.DONE, question="timeout?"),
        make_claim(b, ClaimType.CODE_VERIFIABLE, ClaimStatus.FAILED, question="retries?"),
        make_claim(c, ClaimType.CONCEPTUAL, ClaimStatus.SKIPPED),
    ]
    cov = compute_doc_coverage(sample_doc, claims)

    assert cov.claim_units == 2
    assert cov.resolved_units == 1
    # Some of the document was deemed checkable, but not all of it.
    assert 0.0 < cov.extraction_coverage < 1.0
    # Half the checkable content actually reached a verdict.
    assert cov.resolution_coverage == cov.resolved_chars / cov.claim_chars
    assert cov.resolution_coverage < 1.0


def test_a_failed_claim_is_not_resolved(sample_doc: NormalizedDoc) -> None:
    """FAILED means the machinery broke. It is not a conclusion."""
    unit = sample_doc.units[1]
    claims = [make_claim(unit, ClaimType.CODE_VERIFIABLE, ClaimStatus.FAILED, question="q")]
    cov = compute_doc_coverage(sample_doc, claims)
    assert cov.claim_units == 1
    assert cov.resolved_units == 0
    assert cov.resolution_coverage == 0.0


def test_a_unit_with_no_claim_row_is_a_coverage_gap(sample_doc: NormalizedDoc) -> None:
    """Units without a row must not silently vanish from the denominator."""
    cov = compute_doc_coverage(sample_doc, [])
    assert cov.total_units == 3
    assert cov.claim_units == 0
    assert cov.extraction_coverage == 0.0
    assert cov.counts_by_claim_type[ClaimType.NONE.value] == 3


def test_empty_document_does_not_divide_by_zero() -> None:
    doc = NormalizedDoc(
        id="d",
        run_id="r",
        source_filename="empty.md",
        source_format="md",
        source_sha256="0" * 64,
        text="",
        units=[],
    )
    cov = compute_doc_coverage(doc, [])
    assert cov.extraction_coverage == 0.0
    assert cov.resolution_coverage == 0.0


def test_run_coverage_aggregates(sample_doc: NormalizedDoc) -> None:
    unit = sample_doc.units[1]
    claims = [make_claim(unit, ClaimType.CODE_VERIFIABLE, ClaimStatus.DONE, question="q")]
    per_doc = [compute_doc_coverage(sample_doc, claims)]
    run_cov = compute_run_coverage("run_test", per_doc)
    assert run_cov.total_chars == per_doc[0].total_chars
    assert run_cov.claim_chars == per_doc[0].claim_chars


def test_highlights_tile_the_document(sample_doc: NormalizedDoc) -> None:
    """The visualization tab colours every character, so segments must tile."""
    highlights = build_highlights(sample_doc, [])
    segments = highlights.segments
    assert len(segments) == len(sample_doc.units)
    assert segments[0].span.start == 0
    assert segments[-1].span.end == len(sample_doc.text)
    for a, b in zip(segments[:-1], segments[1:], strict=True):
        assert a.span.end == b.span.start


def test_highlights_carry_the_verdict(sample_doc: NormalizedDoc) -> None:
    from docverify.models import Judgement

    unit = sample_doc.units[1]
    claim = make_claim(unit, ClaimType.CODE_VERIFIABLE, ClaimStatus.DONE, question="q")
    claim.judgement = Judgement(verdict=Verdict.INCORRECT)

    highlights = build_highlights(sample_doc, [claim])
    seg = next(s for s in highlights.segments if s.unit_id == unit.id)
    assert seg.verdict is Verdict.INCORRECT
    assert seg.claim_id == claim.id
