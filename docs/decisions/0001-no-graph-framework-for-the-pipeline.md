# 0001. No graph framework for the pipeline

Status: accepted

## Context

The pipeline is a fixed four-step DAG with per-claim fan-out. LangGraph was
the obvious candidate, particularly because it offers checkpointing and we
want to resume runs without repeating expensive work.

## Decision

**The pipeline orchestration is a plain loop plus the claim table.**

**LangGraph inside the `investigate` stage is fine**, and probably a good fit.
It sits behind the stage interface and nothing above it learns about it.

**LangChain proper is not used.** The LLM router talks to endpoints directly.

## Why

The claim table has to exist regardless. The dashboards need it: three verdict
tabs, coverage cards, per-claim human notes. Once it exists, resume is:

```sql
SELECT * FROM claims WHERE run_id = ? AND status != 'done'
```

and a re-enqueue. Roughly twenty lines. Checkpointing is not a reason to adopt
a framework, because we get it free from something we must build anyway.

Adopting a framework checkpointer means **two persistence mechanisms** for run
state: its tables in its serialisation format, and our claim table that the UI
queries. Two sources of truth for the same thing is a reliable bug generator,
and when they disagree, finding out which is right is a bad day.

There is also a capability we would lose. Because every stage output is a
column on the claim row, we get:

```
dv run --resume run_abc123 --from judge
```

Re-judge a finished run reusing every stored investigation. Change a prompt,
re-judge three hundred claims in minutes, skip the expensive agentic stage.
For a project where prompt iteration is most of the work, that is the single
most valuable developer feature in the system.

Only the `investigate` stage is genuinely agentic: a ReAct loop over tools
with a stopping decision. That is where a framework earns its keep, so it is
allowed there.

LangChain is excluded for a narrower reason. The router's job is to reach an
internal endpoint, an OpenAI-spec endpoint and Gemini. Internal vLLM/TGI
deployments and most gateways already speak the OpenAI chat-completions shape,
so the shared wire format is the abstraction. Adding another one over the top
is where the time goes to fighting leaks rather than writing the forty lines
that would have worked.

## Consequences

- The orchestrator is ours to write and to debug. It is about 150 lines.
- Retries, backoff and concurrency are explicit in `orchestrator.py` and
  `llm/router.py` rather than configured in a framework.
- If LangGraph is later adopted for the pipeline anyway, the requirement that
  survives is: **the claim table remains the only source of run state the UI
  reads.**
