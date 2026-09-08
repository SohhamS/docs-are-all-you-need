"""Shared fixtures.

Everything here is offline. No network, no API key, no inference endpoint, no
code server. A test that needs a real model is testing the model, not this
code.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from docverify import ids
from docverify.codetools.fake import FakeCodeTools
from docverify.config import Config, load_config
from docverify.models import (
    Claim,
    ClaimStatus,
    ClaimType,
    DocFormat,
    NormalizedDoc,
    Span,
    Unit,
    UnitKind,
)

FAKE_REF = "a" * 40

# A tiny multi-language repository. Deliberately contains a fact the sample
# document gets right and one it gets wrong, so an end-to-end test has
# something real to find.
FAKE_FILES: dict[str, str] = {
    "src/config/server.go": (
        "package config\n"
        "\n"
        'import "time"\n'
        "\n"
        "// Config controls the client.\n"
        "type Config struct {\n"
        "    RequestTimeout time.Duration\n"
        "    MaxRetries     int\n"
        "}\n"
        "\n"
        "// DefaultConfig returns the default client configuration.\n"
        "func DefaultConfig() Config {\n"
        "    return Config{\n"
        "        RequestTimeout: 30 * time.Second,\n"
        "        MaxRetries:     5,\n"
        "    }\n"
        "}\n"
    ),
    "src/api/handler.py": (
        "MAX_PAGE_SIZE = 100\n"
        "\n"
        "\n"
        "def list_items(page_size: int = 20) -> list[dict]:\n"
        '    """Return one page of items."""\n'
        "    if page_size > MAX_PAGE_SIZE:\n"
        "        raise ValueError('page_size exceeds MAX_PAGE_SIZE')\n"
        "    return []\n"
    ),
}


@pytest.fixture
def config() -> Config:
    """The committed default configuration."""
    return load_config("config/default.yaml")


@pytest.fixture
def minimal_config() -> Config:
    """Defaults only, for tests that should not depend on the YAML file."""
    return Config()


@pytest.fixture
def codetools() -> FakeCodeTools:
    return FakeCodeTools(FAKE_FILES, repo="fake/repo", ref=FAKE_REF)


@pytest.fixture
def sample_text() -> str:
    return (
        "# Client configuration\n"
        "\n"
        "The default request timeout is 30 seconds.\n"
        "The client retries up to 3 times before giving up.\n"
        "We designed this to be simple to reason about.\n"
    )


@pytest.fixture
def sample_doc(sample_text: str) -> NormalizedDoc:
    """A hand-segmented document, so tests do not depend on `segment()`.

    Units tile `sample_text` completely: that property is what the coverage
    arithmetic rests on, and asserting it here keeps these tests honest even
    while the real segmenter is unimplemented.
    """
    doc_sha = ids.sha256_text(sample_text)
    boundaries = [
        (0, 24, UnitKind.HEADING),
        (24, 67, UnitKind.SENTENCE),
        (67, 119, UnitKind.SENTENCE),
        (119, len(sample_text), UnitKind.SENTENCE),
    ]
    units = [
        Unit(
            id=ids.unit_id(doc_sha, i, start, end),
            doc_id="doc_test",
            ordinal=i,
            kind=kind,
            span=Span(start=start, end=end),
            text=sample_text[start:end],
            heading_path=[] if kind is UnitKind.HEADING else ["Client configuration"],
        )
        for i, (start, end, kind) in enumerate(boundaries)
    ]
    return NormalizedDoc(
        id="doc_test",
        run_id="run_test",
        source_filename="sample_doc.md",
        source_format=DocFormat.MD,
        source_sha256=doc_sha,
        title="Client configuration",
        text=sample_text,
        units=units,
    )


def make_claim(
    unit: Unit,
    claim_type: ClaimType,
    status: ClaimStatus = ClaimStatus.PENDING,
    question: str = "",
    doc_answer: str = "",
) -> Claim:
    """Build a claim row for tests."""
    now = datetime.now(UTC)
    return Claim(
        id=ids.claim_id("sha", unit.id, question or unit.text),
        run_id="run_test",
        doc_id=unit.doc_id,
        unit_id=unit.id,
        claim_type=claim_type,
        question=question,
        doc_answer=doc_answer,
        raw_text=unit.text,
        status=status,
        created_at=now,
        updated_at=now,
    )
