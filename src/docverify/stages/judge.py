"""Stage 4: the verdict, and the patch when the document is wrong.

This is the first stage that sees both answers. Everything before it was
arranged so that this comparison means something.

ASYMMETRY IS DELIBERATE
-----------------------
INCORRECT must clear a higher bar than CORRECT.

A false INCORRECT costs a bad edit to a real document plus the reviewer's
trust, and you will usually never hear about it. A false UNVERIFIABLE costs
one human glance. So when the evidence is thin, when the answers differ in a
way that might be phrasing rather than substance, when the sufficiency check
was lukewarm: UNVERIFIABLE. Not INCORRECT.

THE PATCH GETS THE SAME DISCIPLINE AS THE FINDING
-------------------------------------------------
The patch is the artefact that actually reaches a customer's documentation.
It would be strange to verify the finding through four stages and then let
the fix be an unchecked one-shot generation.

So: `new_text` may only assert facts present in `evidence_refs`. It is a span
replacement carrying `old_text_sha256`, checked at apply time, so a document
edited since the run is never silently clobbered. And a "line" is the wrong
unit for prose anyway; a claim can sit mid-paragraph, in a table cell or in a
bullet.

ON "THE CODE IS ALWAYS RIGHT"
-----------------------------
That is this product's working assumption and this stage implements it.

It is not always true. Sometimes the document describes intended behaviour
and the code has a bug. The system cannot tell the difference, so the
mitigation lives in the review flow rather than here: a human dismissing an
INCORRECT finding must give a `DismissalReason`, one of which is
CODE_ISSUE_NOT_DOC_ISSUE. That gives the reviewer an honest exit instead of
a choice between editing a document to describe a bug and quietly losing
faith in the tool. Do not remove it as redundant.
"""

from __future__ import annotations

from pydantic import BaseModel

from docverify.models import (
    Claim,
    EvidenceReport,
    Investigation,
    Judgement,
)
from docverify.stages.base import StageContext


class JudgeRequest(BaseModel):
    """The full bundle. The only stage that sees both sides."""

    claim_id: str
    question: str
    doc_answer: str
    raw_text: str
    unit_id: str
    investigation: Investigation
    evidence_report: EvidenceReport


class JudgeStage:
    """Compare the two answers and decide."""

    name = "judge"

    async def run(self, ctx: StageContext, request: JudgeRequest) -> Judgement:
        """Return the verdict, and a patch when the verdict is INCORRECT.

        Decision order, and the first three need no model at all:

          1. `evidence_report.authenticity.passed` is False
             -> UNVERIFIABLE, reason EVIDENCE_NOT_AUTHENTIC.
          2. `sufficiency.supported` is False
             -> UNVERIFIABLE, reason EVIDENCE_INSUFFICIENT.
          3. `investigation.response_answer` is empty
             -> UNVERIFIABLE, reason NO_EVIDENCE_FOUND or
                TOOL_BUDGET_EXHAUSTED depending on `tool_calls_used`.
          4. Otherwise ask the model to compare `doc_answer` against
             `response_answer` in the light of the evidence.

        Semantic equivalence, not string equality: "30 seconds", "30s" and
        "thirty seconds" are the same answer, and a judge that flags them is
        worse than no judge. Equally, a document that is right about the
        value and wrong about the unit is INCORRECT.

        When the model is not clearly confident, return UNVERIFIABLE. Re-read
        the asymmetry note above before tuning this in the other direction.

        Raises:
            StageError: if the model returns INCORRECT with no usable patch.
                An INCORRECT finding a human cannot act on is noise on the
                one dashboard tab that exists to be acted on.
        """
        raise NotImplementedError

    def build_patch(self, ctx: StageContext, claim: Claim, new_text: str) -> object:
        """Construct the span replacement for an INCORRECT verdict.

        `old_text` is the claim's `raw_text`, `old_text_sha256` its digest,
        `unit_id` the anchor. Verify that `raw_text` still appears in the
        stored document text before returning; if it does not, the document
        drifted and the patch must not be offered.
        """
        raise NotImplementedError
