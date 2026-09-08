"""Stage 1: segment-then-classify.

The document has already been split deterministically into units. This stage
looks at each unit and decides what kind of assertion it makes, and where it
makes a code-checkable one, writes the question and the document's answer.

WHY THIS SHAPE (see ADR 0002)
-----------------------------
The obvious design is "read the document and extract the claims". It fails in
three ways this one does not:

1. It cannot report coverage. A document where twelve of forty claims were
   found looks exactly like a document with twelve claims. The dashboard says
   97% correct and nobody knows the wrong parts were never examined.
2. It cannot be atomic on request. Asking a model to "be atomic" over a whole
   document does not produce atomicity. Splitting first, then classifying one
   unit at a time, does.
3. It needs offsets from the model. Models are unreliable at character
   arithmetic and the highlighting view depends on offsets being exact.

Here, every unit gets a row, so coverage is arithmetic; the unit boundaries
came from the splitter, so offsets are exact; and the model's job is reduced
to a closed classification per unit.

THE HARD REQUIREMENT ON QUESTIONS
---------------------------------
The investigator will never see this document. So every question written here
must be answerable by someone who has never read it.

    bad:  "What is the default timeout?"
    good: "What is the default value of the `request_timeout` option on the
           Go client's Config struct?"

The unit's `heading_path` and the document title are the raw material for
that. A question that only makes sense in context produces a confident wrong
answer downstream, which is worse than no answer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from docverify.models import Claim, ClaimType, NormalizedDoc, Unit
from docverify.stages.base import StageContext


class UnitClassification(BaseModel):
    """The model's verdict on one unit. Note: `unit_id`, never offsets."""

    unit_id: str
    claim_type: ClaimType
    question: str = ""
    doc_answer: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ClassifyResult(BaseModel):
    classifications: list[UnitClassification] = Field(default_factory=list)


class ClassifyStage:
    """Classify every unit of a document and build claim rows."""

    name = "classify"

    async def run(self, ctx: StageContext, doc: NormalizedDoc) -> list[Claim]:
        """Classify all units and return one Claim per unit.

        Returns a Claim for EVERY unit, not only the checkable ones. Units
        that are conceptual, navigational or empty get a Claim with the
        matching `claim_type` and status SKIPPED. The coverage view needs a
        row for every unit to account for every character; a unit with no row
        is a coverage gap and is reported as one.

        Batch units into groups that fit the context window rather than one
        call per unit, and always send unit ids so results can be matched back.

        Raises:
            StageError: if the model returns ids that are not in this document,
                or omits units. Silently dropping either corrupts coverage.
        """
        raise NotImplementedError

    def build_claim(self, doc: NormalizedDoc, unit: Unit, c: UnitClassification) -> Claim:
        """Turn one classification into a Claim row.

        The id comes from `ids.claim_id(doc.source_sha256, unit.id, question)`,
        so re-classifying an unchanged document produces the same ids and
        overwrites rather than duplicates.
        """
        raise NotImplementedError
