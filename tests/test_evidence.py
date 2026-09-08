"""The deterministic authenticity check.

This is the defence against a fabricated citation reaching a human as a
verified finding. Every named check gets a test that makes it fail on its own,
because a check that silently stops working leaves no trace anywhere else.
"""

from __future__ import annotations

import pytest

from docverify.codetools.fake import FakeCodeTools
from docverify.config import Config
from docverify.models import CodeRef, Evidence
from docverify.stages.base import StageContext
from docverify.stages.evidence import check_authenticity
from tests.conftest import FAKE_REF


@pytest.fixture
def ctx(minimal_config: Config, codetools: FakeCodeTools) -> StageContext:
    return StageContext(
        config=minimal_config,
        llm=None,  # type: ignore[arg-type]
        codetools=codetools,
        run_id="run_test",
        doc_id="doc_test",
        claim_id="c_test",
    )


async def real_evidence(codetools: FakeCodeTools, path: str, start: int, end: int) -> Evidence:
    ref = await codetools.read_file(path, line_start=start, line_end=end)
    return Evidence(ref=ref, justification="the default is set here")


async def test_a_genuine_citation_passes(ctx: StageContext, codetools: FakeCodeTools) -> None:
    ev = await real_evidence(codetools, "src/config/server.go", 12, 18)
    result = await check_authenticity(ctx, [ev])
    assert result.passed
    assert all(c.passed for c in result.checks)


async def test_no_citations_fails(ctx: StageContext) -> None:
    """An answer citing nothing cannot be verified, whatever it says."""
    result = await check_authenticity(ctx, [])
    assert not result.passed
    assert result.checks[0].name == "at_least_one_evidence"


async def test_a_fabricated_path_fails(ctx: StageContext) -> None:
    """The case the whole mechanism exists for."""
    ev = Evidence(
        ref=CodeRef(
            repo="fake/repo",
            ref=FAKE_REF,
            path="src/does/not/exist.go",
            line_start=1,
            line_end=5,
            snippet="whatever the model imagined",
            snippet_sha256="0" * 64,
        ),
        justification="I am certain about this",
    )
    result = await check_authenticity(ctx, [ev])
    assert not result.passed
    assert any("resolves_at_commit" in c.name and not c.passed for c in result.checks)


async def test_a_tampered_snippet_fails(ctx: StageContext, codetools: FakeCodeTools) -> None:
    """Real file, real lines, but the snippet does not match what is there.

    Catches a citation reused from a different commit, and a model that
    rewrote the snippet to fit its answer.
    """
    ev = await real_evidence(codetools, "src/config/server.go", 12, 18)
    tampered = Evidence(
        ref=ev.ref.model_copy(update={"snippet_sha256": "1" * 64}),
        justification=ev.justification,
    )
    result = await check_authenticity(ctx, [tampered])
    assert not result.passed


async def test_a_citation_from_another_commit_fails(
    ctx: StageContext, codetools: FakeCodeTools
) -> None:
    """The run pinned one SHA. Evidence from a different one is not evidence
    about the code under test."""
    ev = await real_evidence(codetools, "src/api/handler.py", 1, 3)
    other = Evidence(
        ref=ev.ref.model_copy(update={"ref": "b" * 40}),
        justification=ev.justification,
    )
    result = await check_authenticity(ctx, [other])
    assert not result.passed
    assert any("pinned_ref" in c.name and not c.passed for c in result.checks)


async def test_an_oversized_span_fails(ctx: StageContext, codetools: FakeCodeTools) -> None:
    """A citation spanning most of a file gestures at a file rather than
    evidencing a claim."""
    ev = await real_evidence(codetools, "src/config/server.go", 1, 18)
    result = await check_authenticity(ctx, [ev], max_span_lines=3)
    assert not result.passed
    assert any("span_within_limit" in c.name and not c.passed for c in result.checks)


async def test_one_bad_citation_fails_the_whole_set(
    ctx: StageContext, codetools: FakeCodeTools
) -> None:
    """Mixing a real citation with a fabricated one must not pass. A model
    that cites three real files and one imagined one has still imagined one."""
    good = await real_evidence(codetools, "src/config/server.go", 12, 18)
    bad = Evidence(
        ref=good.ref.model_copy(update={"path": "src/nope.go"}),
        justification="also this",
    )
    result = await check_authenticity(ctx, [good, bad])
    assert not result.passed
