"""Stage 3: check the evidence. Two different questions, never conflated.

    AUTHENTICITY  Does the cited evidence exist, exactly as cited, at the
                  pinned commit? Deterministic. Cheap. Runs on everything.

    SUFFICIENCY   Does that evidence actually support the answer given?
                  Semantic. Needs a model. Also runs on everything.

THE MISTAKE THIS SPLIT EXISTS TO PREVENT
----------------------------------------
The tempting design is: run the deterministic check, and only if it fails,
ask a model. That is wrong, and the failure it produces is the worst one in
the system.

Authenticity passing tells you the model did not invent a file path. It tells
you nothing at all about relevance. An investigator can cite a real file, at
real line numbers, that has nothing to do with the question, pass the
deterministic check, and arrive at the judge with a confidently wrong answer
wearing a badge that reads "evidence verified". The judge then compares that
wrong answer against a correct document and marks correct documentation as
incorrect. A human applies the suggested patch and a good document is
damaged.

So: both checks, every claim, always.

WHY A FAILED AUTHENTICITY CHECK IS TERMINAL
-------------------------------------------
If the file does not exist, or the line range is out of bounds, or the
snippet no longer hashes to what was cited, the citation is fabricated or
stale. No amount of model reasoning makes a fabricated citation real. Mark
the claim UNVERIFIABLE with reason EVIDENCE_NOT_AUTHENTIC and stop. Sending
it to a model spends a call to reach a conclusion already in hand.

The one genuinely recoverable case, a real citation written in a slightly
wrong format, is prevented upstream by the tool contract rather than repaired
here. See `codetools/protocol.py`.
"""

from __future__ import annotations

from docverify.models import (
    AuthenticityResult,
    CheckResult,
    Evidence,
    EvidenceReport,
    Investigation,
)
from docverify.stages.base import StageContext


async def check_authenticity(
    ctx: StageContext,
    evidences: list[Evidence],
    *,
    require_at_least_one: bool = True,
    max_span_lines: int = 400,
) -> AuthenticityResult:
    """Deterministic checks over the citations. No model involved.

    Fully implemented, because it is deterministic and because it is the part
    of the system that must never quietly change behaviour.
    """
    checks: list[CheckResult] = []

    if require_at_least_one and not evidences:
        checks.append(
            CheckResult(
                name="at_least_one_evidence",
                passed=False,
                detail="the answer cites nothing, so nothing can be verified",
            )
        )
        return AuthenticityResult(passed=False, checks=checks)

    checks.append(CheckResult(name="at_least_one_evidence", passed=True))

    for i, ev in enumerate(evidences):
        ref = ev.ref
        prefix = f"evidence[{i}] {ref.path}:{ref.line_start}-{ref.line_end}"

        # The citation must belong to the commit this run pinned. A ref from
        # another commit is not evidence about the code under test.
        pinned = ref.ref == ctx.codetools.ref
        checks.append(
            CheckResult(
                name=f"{prefix} pinned_ref",
                passed=pinned,
                detail=""
                if pinned
                else f"cites {ref.ref[:12]}, run pinned {ctx.codetools.ref[:12]}",
            )
        )

        ordered = ref.line_start <= ref.line_end
        checks.append(
            CheckResult(
                name=f"{prefix} line_range_ordered",
                passed=ordered,
                detail="" if ordered else "line_start is after line_end",
            )
        )

        # A citation spanning most of a file is a gesture at a file, not
        # evidence for a specific claim.
        span_ok = (ref.line_end - ref.line_start + 1) <= max_span_lines
        checks.append(
            CheckResult(
                name=f"{prefix} span_within_limit",
                passed=span_ok,
                detail="" if span_ok else f"spans more than {max_span_lines} lines",
            )
        )

        # The decisive check: does this resolve, byte for byte, right now?
        resolves = await ctx.codetools.verify_ref(ref)
        checks.append(
            CheckResult(
                name=f"{prefix} resolves_at_commit",
                passed=resolves,
                detail="" if resolves else "path, line range or snippet hash does not match",
            )
        )

    return AuthenticityResult(passed=all(c.passed for c in checks), checks=checks)


class EvidenceStage:
    """Authenticity, then sufficiency. Both, always."""

    name = "evidence"

    async def run(self, ctx: StageContext, investigation: Investigation) -> EvidenceReport:
        """Produce the evidence report for one investigation.

        Order:
          1. `check_authenticity`. If it fails, return immediately with
             `sufficiency=None`. Terminal; no model call.
          2. Otherwise ask the model whether the citations support
             `response_answer`, and return both results.

        The sufficiency prompt must be given the citation snippets and the
        answer, and nothing about the document. This stage is downstream of
        the blindness rule and does not get to break it either.
        """
        raise NotImplementedError
