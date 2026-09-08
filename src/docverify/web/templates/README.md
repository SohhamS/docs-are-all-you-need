# Dashboard templates

Jinja2 templates for the server-rendered UI. Not yet written.

Pages to build:

- `runs.html` — the runs list
- `run.html` — one run: summary cards, then tabs
- `document.html` — the visualization tab

## The summary cards

Must show **both** coverage ratios, not just verdict counts:

    extraction coverage   how much of the document was considered checkable
    resolution coverage   how much of that reached a verdict

Verdict counts alone let a run that examined a third of a document look like
a clean bill of health. See `docs/coverage.md`.

Also show the failed and skipped counts. Failed is its own tab: an
infrastructure error is not an ambiguous claim, and putting crashes in front
of a technical writer trains them to ignore the queue.

## The visualization tab

`GET /api/runs/{run_id}/docs/{doc_id}/highlights` returns `DocHighlights`:
the document text plus segments that tile it completely. Render the text and
colour every character by its segment.

    purple    no claim (none, navigational)
    grey      skipped (conceptual, behavioural)
    green     correct
    red       incorrect
    amber     unverifiable
    outlined  failed

Clicking a segment opens that claim: the question, both answers, the
citations with their snippets, both evidence checks, the judgement, and the
comment box.

## Dismissing an incorrect finding

The dismissal control requires a reason. `CODE_ISSUE_NOT_DOC_ISSUE` must be
one of the options offered. See `AGENTS.md` invariant 14.
