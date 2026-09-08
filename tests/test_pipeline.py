"""End-to-end tests. These fail until the stubs are implemented.

They are written first on purpose. Each one describes a behaviour the finished
system must have, in executable form, so "done" is not a matter of opinion.

Run them with:

    pytest tests/test_pipeline.py -m '' --runxfail

to see exactly what is left.
"""

from __future__ import annotations

import pytest

from docverify.codetools.fake import FakeCodeTools
from docverify.config import Config

pytestmark = pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="skeleton")


# --- ingest ----------------------------------------------------------------


def test_segment_produces_a_complete_partition(sample_text: str) -> None:
    """The property every coverage number rests on. See ADR 0002."""
    from docverify.ingest.segment import assert_partition, segment
    from docverify.models import DocFormat, NormalizedDoc

    doc = NormalizedDoc(
        id="d",
        run_id="r",
        source_filename="s.md",
        source_format=DocFormat.MD,
        source_sha256="0" * 64,
        text=sample_text,
        units=[],
    )
    units = segment(doc)
    assert_partition(sample_text, units)


def test_segment_does_not_split_inside_a_code_block() -> None:
    from docverify.ingest.segment import segment
    from docverify.models import DocFormat, NormalizedDoc

    text = "Intro line.\n\n```python\nx = 1\ny = 2\n```\n\nOutro line.\n"
    doc = NormalizedDoc(
        id="d",
        run_id="r",
        source_filename="s.md",
        source_format=DocFormat.MD,
        source_sha256="0" * 64,
        text=text,
        units=[],
    )
    units = segment(doc)
    code_units = [u for u in units if "x = 1" in u.text]
    assert len(code_units) == 1, "a fenced block is one unit"
    assert "y = 2" in code_units[0].text


def test_segment_does_not_break_on_abbreviations() -> None:
    from docverify.ingest.segment import segment
    from docverify.models import DocFormat, NormalizedDoc

    text = "Use v1.2.3 or later, e.g. the latest release. Then restart.\n"
    doc = NormalizedDoc(
        id="d",
        run_id="r",
        source_filename="s.md",
        source_format=DocFormat.MD,
        source_sha256="0" * 64,
        text=text,
        units=[],
    )
    sentences = [u for u in segment(doc) if u.text.strip()]
    assert len(sentences) == 2, f"expected 2 sentences, got {[u.text for u in sentences]}"


def test_a_scanned_pdf_is_rejected(tmp_path, minimal_config: Config) -> None:  # type: ignore[no-untyped-def]
    """Refusing is the honest failure. Claims from garbled text still produce
    confident-looking verdicts. See ADR 0005."""
    from docverify.ingest.loader import ScannedPdfError, load

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% no text layer\n")
    with pytest.raises(ScannedPdfError):
        load(pdf, "run_test", minimal_config.ingest)


# --- classify --------------------------------------------------------------


async def test_classify_returns_a_row_for_every_unit(sample_doc, minimal_config) -> None:  # type: ignore[no-untyped-def]
    """AGENTS.md invariant 8. A unit without a row is a coverage gap."""
    from docverify.stages.base import StageContext
    from docverify.stages.classify import ClassifyStage

    ctx = StageContext(
        config=minimal_config,
        llm=None,
        codetools=None,  # type: ignore[arg-type]
        run_id="run_test",
        doc_id=sample_doc.id,
    )
    claims = await ClassifyStage().run(ctx, sample_doc)
    assert {c.unit_id for c in claims} == {u.id for u in sample_doc.units}


async def test_classify_skips_conceptual_statements(sample_doc, minimal_config) -> None:  # type: ignore[no-untyped-def]
    """ "We designed this to be simple" is not something code can settle. It
    must not reach a human's review queue."""
    from docverify.models import ClaimStatus, ClaimType
    from docverify.stages.base import StageContext
    from docverify.stages.classify import ClassifyStage

    ctx = StageContext(
        config=minimal_config,
        llm=None,
        codetools=None,  # type: ignore[arg-type]
        run_id="run_test",
        doc_id=sample_doc.id,
    )
    claims = await ClassifyStage().run(ctx, sample_doc)
    conceptual = [c for c in claims if "designed this" in c.raw_text]
    assert conceptual and conceptual[0].claim_type is ClaimType.CONCEPTUAL
    assert conceptual[0].status is ClaimStatus.SKIPPED


# --- judge -----------------------------------------------------------------


async def test_judge_treats_equivalent_phrasings_as_correct(minimal_config: Config) -> None:
    """ "30 seconds" and "30s" are the same answer. A judge that flags them is
    worse than no judge."""
    from docverify.models import (
        AuthenticityResult,
        EvidenceReport,
        Investigation,
        SufficiencyResult,
        Verdict,
    )
    from docverify.stages.base import StageContext
    from docverify.stages.judge import JudgeRequest, JudgeStage

    ctx = StageContext(
        config=minimal_config,
        llm=None,
        codetools=None,  # type: ignore[arg-type]
        run_id="r",
        claim_id="c",
    )
    request = JudgeRequest(
        claim_id="c",
        question="What is the default request timeout?",
        doc_answer="30 seconds",
        raw_text="The default request timeout is 30 seconds.",
        unit_id="u",
        investigation=Investigation(question="q", response_answer="30s"),
        evidence_report=EvidenceReport(
            authenticity=AuthenticityResult(passed=True),
            sufficiency=SufficiencyResult(supported=True, confidence=0.95, reasoning="ok"),
        ),
    )
    assert (await JudgeStage().run(ctx, request)).verdict is Verdict.CORRECT


async def test_unsupported_evidence_never_yields_incorrect(minimal_config: Config) -> None:
    """AGENTS.md invariant 6. A false INCORRECT damages a real document."""
    from docverify.models import (
        AuthenticityResult,
        EvidenceReport,
        Investigation,
        SufficiencyResult,
        UnverifiableReason,
        Verdict,
    )
    from docverify.stages.base import StageContext
    from docverify.stages.judge import JudgeRequest, JudgeStage

    ctx = StageContext(
        config=minimal_config,
        llm=None,
        codetools=None,  # type: ignore[arg-type]
        run_id="r",
        claim_id="c",
    )
    request = JudgeRequest(
        claim_id="c",
        question="What is the default request timeout?",
        doc_answer="30 seconds",
        raw_text="The default request timeout is 30 seconds.",
        unit_id="u",
        investigation=Investigation(question="q", response_answer="5 seconds"),
        evidence_report=EvidenceReport(
            authenticity=AuthenticityResult(passed=True),
            sufficiency=SufficiencyResult(
                supported=False, confidence=0.2, reasoning="cited code is unrelated"
            ),
        ),
    )
    judgement = await JudgeStage().run(ctx, request)
    assert judgement.verdict is Verdict.UNVERIFIABLE
    assert judgement.unverifiable_reason is UnverifiableReason.EVIDENCE_INSUFFICIENT


# --- orchestrator ----------------------------------------------------------


async def test_run_pins_a_commit_sha(minimal_config: Config, codetools: FakeCodeTools) -> None:
    """AGENTS.md invariant 9. A run that follows a moving branch is not
    reproducible."""
    from docverify.orchestrator import Orchestrator

    orch = Orchestrator(minimal_config, None, None, None, codetools)  # type: ignore[arg-type]
    run = await orch.start_run(["tests/fixtures/sample_doc.md"])
    assert len(run.code_ref) == 40
    assert run.code_ref != "main"


async def test_resume_from_a_stage_reuses_stored_investigations(
    minimal_config: Config,
) -> None:
    """The developer loop: change the judge prompt, re-judge in minutes,
    without repeating the expensive agentic stage. See ADR 0004."""
    from docverify.models import Stage
    from docverify.orchestrator import Orchestrator

    orch = Orchestrator(minimal_config, None, None, None, None)  # type: ignore[arg-type]
    await orch.resume_run("run_test", from_stage=Stage.JUDGE)


async def test_a_crashed_claim_is_failed_and_has_no_verdict(minimal_config: Config) -> None:
    """AGENTS.md invariant 7. Infrastructure errors must not reach the
    unverified review queue."""
    from docverify.models import Stage
    from docverify.orchestrator import Orchestrator

    orch = Orchestrator(minimal_config, None, None, None, None)  # type: ignore[arg-type]
    await orch._worker(Stage.INVESTIGATE)
