"""Tests for the invariants in AGENTS.md that can be checked mechanically.

These are cheap and they catch the kind of change that looks harmless in a
diff. A reviewer will not notice `doc_answer` being added to an investigation
request; this file will.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "docverify"


def module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


# --- invariant 1: the investigator is blind --------------------------------


def test_investigation_request_cannot_carry_the_document_answer() -> None:
    """AGENTS.md invariant 1.

    Comparing the code's answer to the document's answer only means something
    if the investigator reached its answer independently.
    """
    from docverify.stages.investigate import InvestigationRequest

    fields = set(InvestigationRequest.model_fields)
    assert "doc_answer" not in fields, (
        "InvestigationRequest must never carry doc_answer. See ADR 0003."
    )
    assert "raw_text" not in fields, "InvestigationRequest must never carry raw_text. See ADR 0003."


# --- invariant 11: layering ------------------------------------------------


FORBIDDEN_IN_STAGES = {
    "docverify.store",
    "docverify.store.protocol",
    "docverify.store.sqlite",
    "docverify.bus",
    "docverify.orchestrator",
    "docverify.api",
}


@pytest.mark.parametrize("path", sorted((SRC / "stages").glob("*.py")), ids=lambda p: p.name)
def test_stages_do_not_import_infrastructure(path: Path) -> None:
    """AGENTS.md invariant 11.

    Stages take values and return values. This is what makes them testable
    without infrastructure and what keeps a store or bus swap small.
    """
    offenders = module_imports(path) & FORBIDDEN_IN_STAGES
    assert not offenders, f"{path.name} imports {offenders}; see RULES.md, Layering"


def test_models_does_not_import_the_rest_of_the_package() -> None:
    """models.py is the specification and must stay dependency-free."""
    imports = {m for m in module_imports(SRC / "models.py") if m.startswith("docverify")}
    assert imports <= {"docverify.ids"}, f"models.py should not import {imports}"


# --- invariant 7: status and verdict are different -------------------------


def test_status_and_verdict_do_not_overlap() -> None:
    """AGENTS.md invariant 7.

    A crashed claim is FAILED with no verdict. If 'failed' ever appears as a
    verdict, infrastructure errors start landing in a technical writer's
    review queue.
    """
    from docverify.models import ClaimStatus, Verdict

    assert not ({v.value for v in Verdict} & {s.value for s in ClaimStatus})


def test_a_claim_without_a_judgement_has_no_verdict(sample_doc) -> None:  # type: ignore[no-untyped-def]
    from docverify.models import ClaimType
    from tests.conftest import make_claim

    claim = make_claim(sample_doc.units[1], ClaimType.CODE_VERIFIABLE)
    assert claim.verdict is None


# --- invariant 4: sufficiency is not optional ------------------------------


def test_evidence_report_shape_encodes_the_two_checks() -> None:
    """AGENTS.md invariant 4.

    `sufficiency` is None exactly when authenticity failed. Any other None is
    a skipped check, which is the system's worst failure mode.
    """
    from docverify.models import AuthenticityResult, EvidenceReport

    report = EvidenceReport(authenticity=AuthenticityResult(passed=False))
    assert report.sufficiency is None


# --- config sanity ---------------------------------------------------------


def test_default_config_loads_and_stages_resolve_a_provider() -> None:
    from docverify.config import load_config

    cfg = load_config("config/default.yaml")
    for stage in ("classify", "investigate", "evidence", "judge"):
        assert cfg.provider_for(stage) is not None


def test_environment_overrides_beat_the_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mechanism a container uses to retune without editing the file."""
    from docverify.config import load_config

    monkeypatch.setenv("DV__STAGES__INVESTIGATE__CONCURRENCY", "16")
    cfg = load_config("config/default.yaml")
    assert cfg.stages.investigate.concurrency == 16
