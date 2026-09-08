# Architecture

## Shape

A fixed four-stage pipeline with per-claim fan-out, a claim table that is both
the work queue and the checkpoint, and swappable adapters at four seams.

```
                     ┌──────────────┐
   CLI / API  ──────▶│ Orchestrator │◀────── the only module that knows
                     └──────┬───────┘        about both the store and the bus
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          ┌───────┐    ┌────────┐    ┌────────┐
          │ Store │    │  Bus   │    │ Stages │
          └───┬───┘    └────────┘    └───┬────┘
              │                          │
       claims, docs,               classify / investigate
       runs, coverage              evidence / judge
                                          │
                            ┌─────────────┴────────────┐
                            ▼                          ▼
                     ┌────────────┐            ┌──────────────┐
                     │ LLM Router │            │  CodeTools   │
                     └─────┬──────┘            └──────┬───────┘
                           │                          │
              internal / OpenAI-spec / Gemini    MCP code server
```

## The seams

Four interfaces, each with a working fake and a real implementation:

| Seam | Interface | Phase 1 | Later |
|---|---|---|---|
| Persistence | `store/protocol.py` | SQLite | Postgres |
| Transport | `bus.py` | `asyncio.Queue` | Redis Streams |
| Inference | `llm/router.py` | OpenAI-compatible | anything |
| Code access | `codetools/protocol.py` | MCP server | anything |

Only `store/`, `bus.py` and `orchestrator.py` know that a database or a queue
exists. Stages take values and return values. That is what keeps the swap to
Postgres or Redis a change to two or three files, and it is what makes every
stage testable with no infrastructure at all.

## Why no graph framework for the pipeline

See ADR 0001. The pipeline is a fixed DAG with one genuinely agentic node.
A framework would own the control flow and bring a second persistence
mechanism that the dashboards cannot query. The claim table has to exist
anyway for the dashboards, and once it does, resume and checkpointing are a
query and a re-enqueue.

LangGraph inside the `investigate` stage is a different matter and is fine.
It sits behind the stage interface and nothing above it learns about it.

## Load control

The only throttle that matters is the limiter in `llm/router.py`: a
concurrency cap plus a token bucket.

Sequencing documents does **not** bound load. The fan-out to parallel claims
happens inside a document, so peak concurrency is set by claim-level
parallelism and processing documents one at a time only reduces throughput.
`run.docs_concurrency` is a throughput knob, not a safety mechanism.

## Observability

Two stores, one boundary:

- **The store** holds state and results. Claims, verdicts, evidence, coverage,
  human notes. Everything the UI queries or a human acts on.
- **Langfuse** holds traces and reasoning. Tool call sequences, token counts,
  latency, why the agent did what it did.

Nothing the product depends on may live only in a trace. Tracing wraps the LLM
client rather than each stage, so every call is traced with run, document and
claim ids attached, and no stage carries tracing code. It is optional and the
application runs correctly with it switched off.

## Configuration

Precedence: field defaults, then the YAML file, then environment variables
prefixed `DV__` with `__` as the nesting separator.

```bash
DV__STAGES__INVESTIGATE__CONCURRENCY=16
DV__LLM__LIMITER__MAX_IN_FLIGHT=4
```

This is deliberately the shape a ConfigMap plus `env:` entries would take, so
that moving to Kubernetes later is a packaging change and not a code change.
No Kubernetes manifests exist in this repository, and none should be added
until they are needed.

Secrets come from the environment only, and never appear in a config snapshot
or a log line.

## Deployment

One container, one process, everything in it. `docker/compose.yaml` mounts the
config, a data volume for SQLite, and the repository under verification.

The path to splitting stages into separate services is: implement `RedisBus`,
flip `bus.kind`, run `dv worker --stage investigate` as its own service.
Nothing in `stages/` changes. Do not build it before it is needed.
