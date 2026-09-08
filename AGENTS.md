# AGENTS.md

Read this before writing or changing code in this repository. It is for
humans and for AI coding assistants alike.

This file holds the **invariants**: the decisions that the rest of the design
rests on. Breaking one of them does not produce a compiler error. It produces
a system that appears to work and quietly gives wrong answers, which is the
only failure mode that actually matters here, because the output of this
system is "your documentation is wrong, here is the fix" and somebody acts on
it.

Each rule states its reason. The reason matters more than the rule: it lets
you generalise to the case nobody wrote down.

---

## What this system does

It takes a documentation file, breaks it into atomic assertions, answers each
assertion's underlying question independently from the source code, compares
the two answers, and reports each assertion as **correct**, **incorrect** (with
a proposed correction) or **unverifiable** (needs a human).

The pipeline is four stages, per claim:

```
ingest + segment        deterministic, no LLM
   -> classify          LLM: what kind of assertion is this unit?
   -> investigate       LLM + code tools: answer the question, blind
   -> evidence          deterministic check, then LLM sufficiency check
   -> judge             LLM: compare, decide, propose a patch
```

---

## The invariants

### 1. The investigator never sees the document's answer

`InvestigationRequest` carries the question and light scoping context. It does
not carry `doc_answer` and it does not carry `raw_text`.

**Why.** Comparing the investigator's answer to the document's answer only
means something if the two were reached independently. Show the model what the
document claims and it drifts toward confirming it. The correct bucket inflates
and the pipeline becomes an expensive way to agree with whatever was already
written.

This gets violated by well-meaning suggestions: *"the investigator keeps
missing things, let's give it more context."* The fix is a better question at
classify time, never a leak here.

### 2. Language models never produce character offsets

Offsets come from `ingest/segment.py` and nowhere else. Models receive **unit
ids** and return **unit ids**.

**Why.** Models are unreliable at character arithmetic in a way that is easy to
miss and expensive to debug. The highlighting view and every coverage number
depend on offsets being exact.

### 3. Citations are selected, never typed

Every `CodeRef` must come from a `CodeTools` call. The model picks among refs
it was handed; it never writes a path or a line number.

Enforce this in code, not in the prompt: keep returned refs in a dict keyed by
an opaque id, expose only ids to the model, resolve ids back to refs when
building output. A model cannot fabricate a citation it is never allowed to
spell.

**Why.** The deterministic authenticity check is only possible because
citations are structurally verifiable, and that check is what stops a
hallucinated file path from becoming a confident "your documentation is wrong"
on somebody's dashboard.

### 4. Authenticity and sufficiency are both checked, on every claim

- **Authenticity**: does the cited evidence exist, exactly as cited, at the
  pinned commit? Deterministic.
- **Sufficiency**: does that evidence support the answer given? Semantic.

Never skip sufficiency because authenticity passed.

**Why.** Authenticity passing means the model did not invent a path. It says
nothing about relevance. An investigator can cite a real file, at real lines,
irrelevant to the question, pass the deterministic check, and reach the judge
with a wrong answer wearing a "verified" badge. The judge then marks correct
documentation as incorrect and a human applies the patch. That is the worst
outcome the system can produce.

### 5. A failed authenticity check is terminal

Fabricated or stale citation, mark `UNVERIFIABLE` with reason
`EVIDENCE_NOT_AUTHENTIC`, stop. Do not ask a model about it.

**Why.** No amount of reasoning makes a fabricated citation real. The one
recoverable case, a real citation in a wrong format, is prevented upstream by
invariant 3 rather than repaired here.

### 6. `INCORRECT` requires a higher bar than `CORRECT`

When evidence is thin, when the difference might be phrasing, when the
sufficiency check was lukewarm: `UNVERIFIABLE`.

**Why.** A false `INCORRECT` damages a real document and costs the reviewer's
trust, and you will usually never hear about it. A false `UNVERIFIABLE` costs
one human glance.

### 7. Status and verdict are different columns

`ClaimStatus` is *did the machinery work*. `Verdict` is *what did we conclude*.
A crashed claim is `FAILED` with **no verdict**. It is not "unverifiable".

**Why.** They are different queues for different people. File crashes as
unverifiable and the human queue fills with infrastructure failures nobody can
act on, and reviewers learn to ignore it.

### 8. Every unit gets a claim row

Including conceptual, navigational and empty ones, with status `SKIPPED`.

**Why.** Coverage is arithmetic over rows, and the visualization tab colours
every character. A unit with no row is a coverage gap and must be reported as
one, not silently dropped. A document where twelve of forty claims were found
must not look identical to a document with twelve claims.

### 9. The commit is pinned once, at run start

Resolve the branch to a SHA in `start_run`, store it on the run, use it for
every tool call and every `CodeRef`.

**Why.** A run takes a while. If someone merges midway, early and late claims
were checked against different code, the run is not reproducible, and you lose
a day to a bug that is not a bug.

### 10. The store is the only source of run state

The claim row is the checkpoint. Stage outputs are columns on it. Do not put
run state in a framework's own checkpoint tables.

**Why.** The dashboards query this table. Two sources of truth for run state is
a reliable bug generator, and when they disagree you will not enjoy finding
out which one is right.

### 11. Layering

```
stages/          no store, no bus, no orchestrator imports. Values in, values out.
store/, bus.py,
orchestrator.py  the only modules that know a database or queue exists.
models.py        imports nothing from this package except ids.
```

**Why.** This is what makes every stage testable with fakes and no
infrastructure, and what makes swapping SQLite for Postgres or the in-memory
bus for Redis a change to three files.

### 12. Prompts are versioned files

`prompts/<stage>.<version>.md`. Every stored result records the prompt version
and model id that produced it.

**Why.** A verdict from last week must stay explicable after the prompt
changes.

### 13. The patch gets the same discipline as the finding

`new_text` may only assert facts present in `evidence_refs`. It is a span
replacement carrying `old_text_sha256`, checked at apply time.

**Why.** The patch is what actually reaches a customer's documentation. It
would be strange to verify the finding through four stages and let the fix be
an unchecked one-shot generation.

### 14. Dismissing an `INCORRECT` finding requires a reason

`DismissalReason`, including `CODE_ISSUE_NOT_DOC_ISSUE`.

**Why.** The product assumes the code is right. That is not always true, and a
reviewer who hits a genuine code bug needs an honest exit rather than a choice
between editing a document to describe the bug and quietly losing faith in the
tool. It is also the cheapest labelled data this project will ever get.

### 15. No code execution

Phase 1 reads code. It does not run it, and it does not run code samples found
in documents. That is a phase 2 item with its own security review.

---

## Things that look like improvements and are not

- **Giving the investigator the document's answer "for context".** Invariant 1.
- **Skipping the sufficiency check when authenticity passed.** Invariant 4.
  This one looks like a pure cost saving. It is the system's worst failure mode.
- **Asking a model to repair a failed authenticity check.** Invariant 5.
- **Having the model return character offsets so segmentation can be smarter.**
  Invariant 2.
- **Processing documents one at a time to protect the inference cluster.** It
  does not work: the fan-out to parallel claims happens *inside* a document, so
  peak load is unchanged and only throughput drops. The throttle belongs in
  `llm/router.py`.
- **Letting an agent framework own the pipeline's state so resume comes free.**
  Invariant 10. Resume already comes free from the claim table, which has to
  exist anyway.
- **Marking a crashed claim `UNVERIFIABLE` so the counts add up.** Invariant 7.
- **Defaulting to `INCORRECT` when the answers differ.** Invariant 6.

## Where to look

| Question | File |
|---|---|
| What are the types? | `src/docverify/models.py` |
| Why is it built this way? | `docs/decisions/` |
| What must the code MCP server return? | `docs/mcp-tool-spec.md` |
| How is coverage defined? | `docs/coverage.md` |
| How do I add a parser / provider / stage? | `SKILLS.md` |
| Coding conventions? | `RULES.md` |
| What is deferred and why? | `docs/roadmap.md` |
