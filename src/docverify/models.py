"""The domain model. This file is the specification.

Every stage in the pipeline consumes and produces the types defined here.
If you are about to change behaviour, change the type first: a signature that
does not typecheck is a louder objection than a paragraph of prose.

Nothing in this module may import anything from the rest of the package other
than `docverify.ids`. It has no I/O, no database, no network, no LLM.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DocFormat(StrEnum):
    """Input file formats accepted at ingest."""

    DOCX = "docx"
    PDF = "pdf"
    HTML = "html"
    MD = "md"
    TXT = "txt"


class UnitKind(StrEnum):
    """Structural kind of a segmented unit.

    Assigned by the deterministic splitter in `ingest.segment`, never by a
    model. See ADR 0002.
    """

    HEADING = "heading"
    SENTENCE = "sentence"
    LIST_ITEM = "list_item"
    TABLE_CELL = "table_cell"
    CODE_BLOCK = "code_block"
    CAPTION = "caption"
    OTHER = "other"


class ClaimType(StrEnum):
    """What kind of assertion a unit makes.

    Assigned by the `classify` stage. Only CODE_VERIFIABLE units become claims
    that enter the verification pipeline; everything else is recorded with
    status SKIPPED so the coverage view can still colour it.
    """

    CODE_VERIFIABLE = "code_verifiable"
    """A factual assertion that reading the source code can settle."""

    BEHAVIOURAL = "behavioural"
    """About runtime behaviour that would need execution to settle. Phase 2."""

    CONCEPTUAL = "conceptual"
    """Intent, rationale, roadmap, guidance. No code can make it true or false."""

    NAVIGATIONAL = "navigational"
    """Headings, cross-references, table of contents, boilerplate."""

    NONE = "none"
    """Carries no assertion at all."""


class Stage(StrEnum):
    """Pipeline stages, in order. A claim's `stage` field records where it is.

    Resuming a run means re-enqueueing unfinished claims at their recorded
    stage. See ADR 0004.
    """

    CLASSIFY = "classify"
    INVESTIGATE = "investigate"
    EVIDENCE = "evidence"
    JUDGE = "judge"


class ClaimStatus(StrEnum):
    """Processing status. Orthogonal to `Verdict` and never conflated with it.

    A claim can be DONE with verdict UNVERIFIABLE (the system worked, the
    answer was genuinely not determinable) or FAILED with no verdict at all
    (the system broke). Those are different queues for different people.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Verdict(StrEnum):
    """The judge's conclusion. Only set when status is DONE."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNVERIFIABLE = "unverifiable"


class UnverifiableReason(StrEnum):
    """Why a claim could not be settled. Drives triage on the unverified tab."""

    NO_EVIDENCE_FOUND = "no_evidence_found"
    """The investigator searched and found nothing relevant."""

    EVIDENCE_NOT_AUTHENTIC = "evidence_not_authentic"
    """A citation did not resolve against the pinned commit. Terminal; see ADR 0003."""

    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    """Citations resolved but do not support the answer given."""

    AMBIGUOUS_QUESTION = "ambiguous_question"
    """The question could not be answered without the document's own context."""

    TOOL_BUDGET_EXHAUSTED = "tool_budget_exhausted"
    """The investigator hit max_tool_calls before concluding."""

    OTHER = "other"


class DismissalReason(StrEnum):
    """Why a human rejected an INCORRECT finding.

    Required when a human dismisses. Two jobs: it gives the reviewer an honest
    exit when the code is at fault rather than the document, and it is the
    cheapest source of labelled data this project will ever get.
    """

    DOC_IS_FINE = "doc_is_fine"
    CODE_ISSUE_NOT_DOC_ISSUE = "code_issue_not_doc_issue"
    OUT_OF_SCOPE = "out_of_scope"
    TOOL_WAS_WRONG = "tool_was_wrong"
    OTHER = "other"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Document representation
# ---------------------------------------------------------------------------


class Frozen(BaseModel):
    """Base for value objects that must not be mutated after construction."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Span(Frozen):
    """A half-open character range into `NormalizedDoc.text`.

    INVARIANT: spans are produced only by `ingest.segment`. A language model
    must never be asked to produce or adjust offsets; it works with unit ids.
    See ADR 0002.
    """

    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @property
    def length(self) -> int:
        return self.end - self.start


class Unit(Frozen):
    """One atomic piece of a document.

    The units of a document form a complete, non-overlapping, ordered
    partition of its content. That completeness is what makes coverage
    arithmetic rather than guesswork, and what lets the UI colour every
    character of the document.
    """

    id: str
    doc_id: str
    ordinal: int
    kind: UnitKind
    span: Span
    text: str
    heading_path: list[str] = Field(default_factory=list)
    """Ancestor headings, outermost first. Used as investigator context."""


class NormalizedDoc(BaseModel):
    """The single internal representation of an input document.

    Every input format is converted to this at ingest and nothing downstream
    ever sees the original file. `text` is the canonical plain text and all
    spans index into it. See ADR 0005.
    """

    id: str
    run_id: str
    source_filename: str
    source_format: DocFormat
    source_sha256: str
    title: str | None = None
    text: str
    units: list[Unit] = Field(default_factory=list)
    meta: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Code evidence
# ---------------------------------------------------------------------------


class CodeRef(Frozen):
    """A machine-checkable citation into the source repository.

    INVARIANT: a CodeRef is only ever constructed from what a CodeTools call
    returned. The investigator selects among refs it was handed; it never
    types a path or a line number. That is what makes the authenticity check
    in the `evidence` stage possible at all. See docs/mcp-tool-spec.md.
    """

    repo: str
    ref: str
    """Commit SHA. Pinned once at run start and identical across the whole run."""
    path: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    snippet: str
    snippet_sha256: str


class Evidence(Frozen):
    """A citation plus the investigator's reason for offering it."""

    ref: CodeRef
    justification: str
    """Prose, model-written. Example: "the default is set in this function's
    signature". Never a substitute for the ref; always read alongside it."""


class Investigation(BaseModel):
    """Output of the `investigate` stage.

    INVARIANT: the investigator that produced this never saw `doc_answer` or
    `raw_text`. Comparing its answer to the document's is only meaningful
    because it was blind. See ADR 0003.
    """

    question: str
    response_answer: str
    evidences: list[Evidence] = Field(default_factory=list)
    tool_calls_used: int = 0
    model_id: str | None = None
    prompt_version: str | None = None
    trace_id: str | None = None
    """Langfuse trace id. Reasoning lives there, not in the database."""


# ---------------------------------------------------------------------------
# Evidence checking
# ---------------------------------------------------------------------------


class CheckResult(Frozen):
    """One named deterministic check and whether it held."""

    name: str
    passed: bool
    detail: str = ""


class AuthenticityResult(BaseModel):
    """Does the cited evidence exist, exactly as cited, at the pinned commit?

    Purely deterministic. Says nothing whatsoever about whether the evidence
    is relevant to the question; that is `SufficiencyResult`'s job. Conflating
    the two is the mistake this split exists to prevent.
    """

    passed: bool
    checks: list[CheckResult] = Field(default_factory=list)


class SufficiencyResult(BaseModel):
    """Does the cited evidence actually support `response_answer`?

    Semantic, so this needs a model. Runs on every claim whose authenticity
    check passed, never skipped as an optimisation.
    """

    supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    model_id: str | None = None
    prompt_version: str | None = None


class EvidenceReport(BaseModel):
    """Output of the `evidence` stage.

    `sufficiency` is None exactly when `authenticity.passed` is False: a
    fabricated citation is terminal and no model is consulted about it.
    """

    authenticity: AuthenticityResult
    sufficiency: SufficiencyResult | None = None


# ---------------------------------------------------------------------------
# Judgement
# ---------------------------------------------------------------------------


class Patch(Frozen):
    """A proposed replacement for the document text behind an INCORRECT claim.

    A span replacement, not a "line". `old_text_sha256` is checked at apply
    time so a document edited since the run is never silently clobbered.

    INVARIANT: `new_text` may only assert facts present in `evidence_refs`.
    The pipeline verifies findings rigorously; the patch is the artefact that
    actually reaches a customer document, so it gets the same discipline.
    """

    unit_id: str
    old_text: str
    old_text_sha256: str
    new_text: str
    rationale: str
    evidence_refs: list[CodeRef] = Field(default_factory=list)


class Judgement(BaseModel):
    """Output of the `judge` stage.

    Asymmetry is deliberate: INCORRECT requires a higher bar than CORRECT,
    because a false INCORRECT damages a real document and a false
    UNVERIFIABLE costs one human glance. When in doubt, UNVERIFIABLE.
    """

    verdict: Verdict
    unverifiable_reason: UnverifiableReason | None = None
    patch: Patch | None = None
    reasoning: str = ""
    model_id: str | None = None
    prompt_version: str | None = None
    trace_id: str | None = None


class HumanNote(BaseModel):
    """A reviewer's action on a claim. Append-only."""

    created_at: datetime
    author: str | None = None
    comment: str = ""
    dismissal_reason: DismissalReason | None = None
    """Required when dismissing an INCORRECT finding."""
    edited_text: str | None = None
    """A correction the human wrote themselves, superseding any proposed patch."""


# ---------------------------------------------------------------------------
# Claim: the unit of work and the checkpoint record
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """One atomic assertion travelling through the pipeline.

    This is both the unit of work and the checkpoint. Each stage's output is
    stored on the row as it completes, so a stage can be re-run in isolation
    against stored inputs: `dv run --resume <run_id> --from judge` re-judges a
    finished run without touching the expensive investigate stage. See ADR 0004.

    There is exactly one Claim per CODE_VERIFIABLE unit. Units of every other
    ClaimType also get a Claim row, with status SKIPPED and no verdict, so the
    coverage view can account for every character of the document.
    """

    id: str
    """uuid5 over (doc_sha256, unit_id, normalized_question). Deterministic, so
    re-ingesting the same document does not duplicate work."""

    run_id: str
    doc_id: str
    unit_id: str

    claim_type: ClaimType
    question: str = ""
    doc_answer: str = ""
    raw_text: str = ""
    """The document text the claim was drawn from. Never shown to the
    investigator; used by the judge to anchor a patch."""

    stage: Stage = Stage.CLASSIFY
    status: ClaimStatus = ClaimStatus.PENDING
    attempts: int = 0
    error: str | None = None

    investigation: Investigation | None = None
    evidence_report: EvidenceReport | None = None
    judgement: Judgement | None = None
    human_notes: list[HumanNote] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @property
    def verdict(self) -> Verdict | None:
        return self.judgement.verdict if self.judgement else None

    @property
    def is_terminal(self) -> bool:
        return self.status in (ClaimStatus.DONE, ClaimStatus.FAILED, ClaimStatus.SKIPPED)


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class DocCoverage(BaseModel):
    """Coverage for one document. Every field is arithmetic over stored rows.

    Two different numbers, and conflating them hides the failure that matters:

    - `extraction_coverage` is how much of the document was even considered
      checkable. Low means the classifier is missing claims, which is the
      silent failure mode: a document nobody looked at closely looks exactly
      like a document that passed.
    - `resolution_coverage` is how much of the checkable content actually
      reached a verdict rather than dying in a failure.

    Both must be shown. A run reporting 100% correct at 30% extraction
    coverage has verified almost nothing.
    """

    doc_id: str
    total_units: int
    total_chars: int
    claim_units: int
    claim_chars: int
    resolved_units: int
    resolved_chars: int
    counts_by_claim_type: dict[str, int] = Field(default_factory=dict)
    counts_by_verdict: dict[str, int] = Field(default_factory=dict)
    counts_by_status: dict[str, int] = Field(default_factory=dict)

    @property
    def extraction_coverage(self) -> float:
        return (self.claim_chars / self.total_chars) if self.total_chars else 0.0

    @property
    def resolution_coverage(self) -> float:
        return (self.resolved_chars / self.claim_chars) if self.claim_chars else 0.0


class RunCoverage(BaseModel):
    """Coverage across every document in a run."""

    run_id: str
    per_doc: list[DocCoverage] = Field(default_factory=list)
    total_chars: int = 0
    claim_chars: int = 0
    resolved_chars: int = 0
    counts_by_verdict: dict[str, int] = Field(default_factory=dict)
    counts_by_status: dict[str, int] = Field(default_factory=dict)

    @property
    def extraction_coverage(self) -> float:
        return (self.claim_chars / self.total_chars) if self.total_chars else 0.0

    @property
    def resolution_coverage(self) -> float:
        return (self.resolved_chars / self.claim_chars) if self.claim_chars else 0.0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class Run(BaseModel):
    """One verification pass over one or more documents against one commit."""

    id: str
    created_at: datetime
    updated_at: datetime
    status: RunStatus = RunStatus.PENDING

    code_repo: str
    code_ref: str
    """The resolved commit SHA, not a branch name. Resolved once at run start
    and used for every tool call and every CodeRef in the run, so that a merge
    mid-run cannot make the first and last claims disagree. See ADR 0004."""

    declared_version: str | None = None
    """The product version the documents claim to describe. Supplied by the
    operator at upload; not parsed out of the document."""

    doc_ids: list[str] = Field(default_factory=list)
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    """The effective configuration this run used, so a result stays explicable
    after the config file changes."""

    error: str | None = None


# ---------------------------------------------------------------------------
# Highlighting payload for the visualization tab
# ---------------------------------------------------------------------------


class HighlightSegment(Frozen):
    """One coloured span for the document view.

    The segments of a document tile it completely, so the UI can render the
    whole text and every character carries a colour. `claim_id` is None only
    for units that produced no claim row at all.
    """

    span: Span
    unit_id: str
    claim_id: str | None
    claim_type: ClaimType
    status: ClaimStatus
    verdict: Verdict | None


class DocHighlights(BaseModel):
    """Everything the visualization tab needs for one document."""

    doc_id: str
    text: str
    segments: list[HighlightSegment] = Field(default_factory=list)
    coverage: DocCoverage
