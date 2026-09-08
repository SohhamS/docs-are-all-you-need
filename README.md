# docverify

Verifies documentation against source code, one assertion at a time.

Point it at a document. It breaks the document into atomic assertions, answers
each assertion's underlying question independently by reading the code, and
reports every assertion as **correct**, **incorrect** with a proposed
correction, or **unverifiable** and needing a human.

Status: skeleton. The types, contracts, configuration and deterministic parts
are written; the stage implementations are stubs with their contracts
documented in place.

---

## How it works

```
                 ┌─────────────────────────────────────────┐
   document ───▶ │ ingest      parse to one internal format │  deterministic
                 │ segment     split into atomic units      │  no LLM
                 └─────────────────────┬───────────────────┘
                                       │  units tile the document completely
                                       ▼
                 ┌─────────────────────────────────────────┐
                 │ classify    what does this unit assert?  │  LLM
                 └─────────────────────┬───────────────────┘
                                       │  one claim row per unit
                        ┌──────────────┴──────────────┐
                        ▼                              ▼
              code-verifiable                    everything else
                        │                        (skipped, but still
                        ▼                         coloured in the UI)
                 ┌─────────────────────────────────────────┐
                 │ investigate  answer from code, BLIND to  │  LLM + code tools
                 │              what the document said      │
                 └─────────────────────┬───────────────────┘
                                       ▼
                 ┌─────────────────────────────────────────┐
                 │ evidence     do the citations resolve?   │  deterministic
                 │              do they support the answer? │  + LLM
                 └─────────────────────┬───────────────────┘
                                       ▼
                 ┌─────────────────────────────────────────┐
                 │ judge        compare, decide, propose    │  LLM
                 └─────────────────────┬───────────────────┘
                                       ▼
                    correct  │  incorrect (+patch)  │  unverifiable
```

Two properties do most of the work:

**The investigator is blind.** It never sees what the document claims, so
agreement between the two answers is evidence rather than an echo.

**Segmentation is deterministic and complete.** The units tile the document,
so coverage is arithmetic rather than a model's opinion, and the UI can colour
every character of the original text.

---

## Quick start

```bash
pip install -e ".[ingest,dev]"

# End to end with a fake model and a fake repository. No network, no API key.
make smoke

# Against real endpoints, once config/default.yaml points at them.
dv run path/to/doc.md --version v2.3
dv show run_abc123
dv serve
```

## Resuming, and the developer loop

Every stage writes its output onto the claim row, so any stage can be re-run
against stored inputs:

```bash
dv run --resume run_abc123                # continue where it stopped
dv run --resume run_abc123 --from judge   # re-judge, reusing investigations
```

The second one is the loop you will live in. Change the judge prompt, re-judge
three hundred claims in minutes, without repeating the expensive agentic
stage.

---

## Reading coverage

Two numbers, and both are always shown:

- **extraction coverage** — how much of the document was even considered
  checkable.
- **resolution coverage** — how much of that actually reached a verdict.

A run reporting 100% correct at 30% extraction coverage has verified almost
nothing. Verdict counts on their own hide exactly that, which is why the
summary never shows them alone.

---

## Configuration

`config/default.yaml` holds everything tunable. Any value can be overridden by
an environment variable, so a container can be retuned without touching the
file:

```bash
docker run -e DV__STAGES__INVESTIGATE__CONCURRENCY=16 ...
```

Secrets come from the environment only. See `.env.example`.

---

## Where things are

| | |
|---|---|
| `AGENTS.md` | **Read first.** The invariants and why they exist. |
| `RULES.md` | Coding conventions. |
| `SKILLS.md` | Recipes: add a parser, a provider, a stage, a prompt. |
| `src/docverify/models.py` | The domain model. This is the specification. |
| `docs/architecture.md` | How the pieces fit. |
| `docs/mcp-tool-spec.md` | What the code access server must return. |
| `docs/decisions/` | Why it is built this way. |
| `docs/roadmap.md` | What is deliberately deferred. |

---

## Current state

Written and working: the domain model, configuration, logging, coverage
arithmetic, the in-memory bus, the fake code tools, the fake LLM provider, and
the deterministic authenticity check.

Stubbed with contracts documented in the docstring: the parsers, the
segmenter, the four stages, the SQLite store, the LLM router and its real
providers, the MCP code tools, the orchestrator, the API and the CLI.

Blocking unknown: whether the code access server can return line-accurate
citations. `docs/mcp-tool-spec.md` is the specification to settle that
against. Until it is settled, `FakeCodeTools` keeps everything else buildable
and testable.
