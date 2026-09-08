# SKILLS.md

Step-by-step recipes for the changes you will actually make. `AGENTS.md` is
the invariants, `RULES.md` is the conventions, this is the how-to.

---

## Add a document format

1. `src/docverify/ingest/parsers/<format>.py` with
   `parse(data: bytes) -> tuple[str, dict[str, str]]`.
2. Return canonical plain text. Preserve blank lines between blocks, keep code
   blocks verbatim, keep heading markers so the segmenter can build
   `heading_path`.
3. Register it in `ingest/loader.py`'s dispatch and add the extension to
   `IngestConfig.accept_formats`.
4. Add a fixture in `tests/fixtures/` and a test asserting the tiling property
   after segmentation.
5. Add the parsing dependency to the `ingest` extra in `pyproject.toml`.

Do not add offsets in a parser. Offsets are `segment.py`'s job.

---

## Add an LLM provider

1. `src/docverify/llm/providers/<name>.py`, subclass `Provider`, implement
   `complete` and `close`.
2. Map the vendor's response to `Completion`. Every vendor quirk stops in this
   file.
3. Add the literal to `ProviderConfig.kind` and the branch in
   `LLMRouter.provider`.
4. Add an entry under `llm.providers` in `config/default.yaml` with a
   commented example.
5. The API key comes from `api_key_env`, a variable name. Never the key.

If the endpoint speaks OpenAI chat-completions, use `openai_compat` and add a
config entry. Do not write a new class.

---

## Add or change a pipeline stage

1. New module in `src/docverify/stages/`, with a class exposing `name` and
   `async def run(self, ctx: StageContext, payload) -> Result`.
2. Types for its input and output go in `models.py` first. The type is the
   spec; write it before the implementation.
3. Add the stage to the `Stage` enum, to `StagesConfig`, and to
   `Orchestrator._next_stage`.
4. Add a column for its output in `migrations/`, and load/store it in
   `store/sqlite.py`. Without that column the stage cannot be re-run in
   isolation and `--resume --from` stops working for everything after it.
5. No imports of `store`, `bus` or `orchestrator`. See `RULES.md`.

---

## Change a prompt

1. Copy `prompts/<stage>.v1.md` to `<stage>.v2.md` and edit the copy. Do not
   edit v1: finished runs reference it.
2. Bump `stages.<stage>.prompt_version` in `config/default.yaml`.
3. Re-judge an existing run against the new prompt without repeating the
   expensive stages:

   ```
   dv run --resume run_abc123 --from judge
   ```

4. Compare against `tests/golden/`. If there is no labelled set yet, you are
   changing prompts blind; build the set first.

---

## Add a deterministic evidence check

1. Add it inside `check_authenticity` in `stages/evidence.py` as another
   `CheckResult` with a stable `name`.
2. Deterministic only. If it needs a model, it belongs in the sufficiency
   check, not here.
3. Threshold values go in `EvidenceConfig`, not in the function body.
4. Add a test that constructs a citation which fails exactly that check and
   asserts the claim comes out `UNVERIFIABLE` with reason
   `EVIDENCE_NOT_AUTHENTIC`.

---

## Run the pipeline with no LLM and no code server

```
make smoke
```

Uses `FakeProvider` and `FakeCodeTools`. This is how you develop the
orchestrator, the store and the dashboard without an inference endpoint, and
how the whole thing is demoed before the real code MCP server exists.

---

## Write a golden test

1. Put the document in `tests/fixtures/`.
2. Put expected verdicts in `tests/golden/<name>.json`, keyed by the
   question text rather than by claim id, so ids can change without breaking
   the file.
3. Script the fake provider's responses to match what a real model would
   plausibly return.
4. Assert verdicts and both coverage numbers. Coverage regressions are silent
   otherwise, which is the exact failure the coverage numbers exist to catch.

---

## Debug "why did this claim get this verdict"

1. `dv show <run_id> --verdict incorrect` to find the claim id.
2. `GET /api/claims/{claim_id}` returns every stage output: the question, the
   investigator's answer, the citations, both evidence checks, the judgement.
3. Follow `investigation.trace_id` into Langfuse for the tool call sequence
   and the reasoning.
4. Check `evidence_report.authenticity.checks`. A named check that failed
   usually explains the whole verdict on its own.

---

## Move to Postgres, Redis or Kubernetes

Not phase 1 work. When it happens:

- **Postgres**: new class in `store/`, add the literal to `StoreConfig.kind`,
  port `migrations/0001_init.sql`. No stage changes.
- **Redis**: new class in `bus.py` implementing `Bus`, add the literal to
  `BusConfig.kind`. Run `dv worker --stage <name>` as separate services. No
  stage changes.
- **Kubernetes**: `config/default.yaml` becomes a ConfigMap, secrets become
  Secrets, the `DV__` environment overrides already work. No code changes.

The seams exist so these stay small. Do not pre-build them.
