"""Stage 2: answer the question from the code, blind to the document.

THE BLINDNESS RULE (ADR 0003)
-----------------------------
This stage receives the question and a small amount of scoping context. It
does NOT receive `doc_answer` and it does NOT receive `raw_text`.

That is the load-bearing property of the whole system. Comparing this answer
against the document's answer only means something if this answer was reached
independently. Show the model what the document claims and it drifts toward
confirming it, the correct bucket inflates, and the pipeline becomes an
expensive way to agree with whatever was already written.

It is easy to violate this by accident. It usually arrives as a reasonable
sounding suggestion: "the investigator keeps missing things, let us give it
more context." The answer is to improve the question at classify time, not to
leak the answer here.

THE CITATION RULE
-----------------
Every `CodeRef` in the output must be one this stage received from a
`CodeTools` call. The model selects among refs it was handed; it never types
a path or a line number. The deterministic authenticity check in the next
stage depends on it, and that check is what stops a hallucinated file path
from becoming a "your documentation is wrong" on a dashboard.

Enforce it in code, not in the prompt: keep the refs returned by tool calls
in a dict keyed by an opaque id, expose only those ids to the model, and
resolve ids back to refs when building the output. A model cannot fabricate
a citation it is never allowed to spell.

ON THE AGENT HARNESS
--------------------
This is the one genuinely agentic node in the pipeline and the one place
where LangGraph earns its keep. Using it here is fine. It stays behind the
stage interface, so nothing above this file learns about it. Do not let it
own the pipeline's control flow or its state; that belongs to the
orchestrator and the store. See ADR 0001.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from docverify.models import Investigation
from docverify.stages.base import StageContext


class InvestigationRequest(BaseModel):
    """Everything this stage is allowed to know.

    The absence of `doc_answer` and `raw_text` is the point. If you find
    yourself adding them, read ADR 0003 first.
    """

    claim_id: str
    question: str
    doc_title: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    declared_version: str | None = None


class InvestigateStage:
    """Answer a question by reading the repository at the pinned commit."""

    name = "investigate"

    async def run(self, ctx: StageContext, request: InvestigationRequest) -> Investigation:
        """Run the tool loop and return an answer with citations.

        Loop shape:
          1. Offer `search_code`, `read_file` and `list_symbols` as tools.
          2. Let the model call them, up to `config.stages.investigate.max_tool_calls`.
          3. Record every returned `CodeRef` against an opaque id.
          4. Ask for a final answer citing those ids.
          5. Resolve the ids back to refs and build the `Investigation`.

        Rules that must hold:
          - Exhausting the tool budget yields an answer of "" with no
            evidences, which the judge turns into UNVERIFIABLE with reason
            TOOL_BUDGET_EXHAUSTED. It must never produce a guessed answer.
          - Not finding an answer is a legitimate result. An investigator that
            cannot say "I could not determine this" is worse than useless,
            because its confident guesses are indistinguishable from findings.
          - Every `CodeRef` carries `ctx.codetools.ref`, the run's pinned SHA.

        `config.stages.investigate.samples` above 1 means run the loop N times
        and return the answer with citation agreement, recording disagreement
        so the judge can treat it as an UNVERIFIABLE signal. Keep it at 1
        until a labelled set exists to show whether it helps.
        """
        raise NotImplementedError
