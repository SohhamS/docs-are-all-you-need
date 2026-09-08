# RULES.md

Coding conventions. `AGENTS.md` holds the design invariants; this file holds
the mechanical rules. When the two conflict, `AGENTS.md` wins.

## Language and tooling

- Python 3.11 or newer. `from __future__ import annotations` at the top of
  every module.
- Type annotations on every public function, including return types. `mypy`
  runs in strict mode; a new `# type: ignore` needs a comment saying why.
- `ruff` for lint and format. `make lint` before pushing.
- pydantic v2 for anything crossing a boundary: config, stage inputs and
  outputs, API payloads, LLM responses. Plain dataclasses only for internal
  values that never leave the process.

## Layering

Enforced by review, and worth failing a review over:

```
models.py, ids.py       import nothing else from this package
stages/                 may import models, ids, config, llm, codetools
                        MUST NOT import store, bus, orchestrator, api
store/, bus.py          may import models, ids, config
orchestrator.py         may import everything
api/, cli.py            may import everything
```

If a stage needs data it was not handed, pass it in. Do not reach for the
database from inside a stage.

## Async

- Anything doing I/O is `async`. That is every provider, every store method,
  every code tool.
- Never block the event loop. SQLite through `aiosqlite`, or the stdlib driver
  in a thread executor.
- Bound every concurrent fan-out with a semaphore. Unbounded `gather` over a
  document's claims will take out your inference endpoint.
- Every outbound call gets a timeout. No exceptions.

## Errors

- `StageError` means the machinery broke: retry it, and mark the claim
  `FAILED` when retries are exhausted.
- A verdict of `UNVERIFIABLE` means the machinery worked and the answer was
  genuinely not determinable. Never raise to express this and never catch an
  exception and turn it into a verdict.
- Never swallow an exception without logging it with the claim id bound.
- Let `asyncio.CancelledError` propagate.

## Logging

- `structlog` only. No `print`, no bare `logging`. `ruff` flags `print` via
  the `T20` rule.
- Bind `run_id`, `doc_id`, `claim_id` with `logging.bound()` at the top of
  every worker iteration. A log line without them cannot answer the only
  question anyone asks this log file.
- Never log a full document, a full prompt, or a full model response at INFO.
  Log ids, counts and decisions. Reasoning belongs in Langfuse.

## Configuration

- No magic numbers in code. If it is tunable, it belongs in `config/` with a
  default and a docstring explaining what moving it does.
- Secrets come from the environment, never from the YAML file, and never
  appear in a log line or a config snapshot.
- Adding a config field means adding it to `config.py` with a default,
  documenting it in `config/default.yaml`, and mentioning it in the relevant
  doc if it changes behaviour rather than performance.

## Prompts

- Prompts live in `prompts/<stage>.<version>.md`. Never inline in Python.
- Changing a prompt's behaviour means a new version file, not an edit to the
  existing one. Existing runs must stay explicable.
- Bump `prompt_version` in `config/default.yaml` in the same change.
- `render()` does `{{name}}` substitution only. If a prompt needs control
  flow, it needs splitting into two prompts.

## Tests

- Every test runs offline: `FakeProvider` and `FakeCodeTools`, no network, no
  API key, no endpoint. A test that needs a real model is testing the model.
- The tiling property of `segment()` is asserted on every fixture. It is the
  cheapest guard against a whole class of silent coverage bugs.
- Every invariant in `AGENTS.md` that can be tested, is. `test_stages.py`
  already carries the shape for the blindness rule and the authenticity rule.
- Fixtures go in `tests/fixtures/`. Expected verdicts for the labelled set go
  in `tests/golden/`.

## Git

- Small commits with a subject line saying what changed and why.
- A change to anything in `AGENTS.md` needs an ADR in `docs/decisions/`
  explaining what changed and what it now costs. Silent reversals of an
  invariant are the thing this repository is arranged to prevent.
