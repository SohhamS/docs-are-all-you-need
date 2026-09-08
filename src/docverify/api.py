"""HTTP API and the dashboard.

The UI is server-rendered from these endpoints in phase 1. If it later becomes
a separate front end, this module is the contract between the two and nothing
else needs to change.

THE VIEWS
---------
    /                          runs list
    /runs/{run_id}             one run: summary cards, then four tabs
    /runs/{run_id}/document/{doc_id}
                               the visualization tab

The summary cards must show BOTH coverage ratios, not just the verdict
counts. Verdict counts alone let a run that examined a third of a document
look like a clean bill of health.

The tabs are correct, incorrect, unverified, and a fourth for failed. Failed
is separate on purpose: an infrastructure error is not an ambiguous claim,
and putting crashes in front of a technical writer trains them to ignore the
queue.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


def create_app(config_path: str = "config/default.yaml") -> FastAPI:
    """Build the FastAPI application.

    Endpoints to implement:

      GET  /api/runs                          list runs
      GET  /api/runs/{run_id}                 run + RunCoverage
      GET  /api/runs/{run_id}/claims          filter by verdict/status/doc
      GET  /api/runs/{run_id}/docs/{doc_id}/highlights
                                              DocHighlights for the viz tab
      GET  /api/claims/{claim_id}             one claim, all stage outputs
      POST /api/claims/{claim_id}/notes       append a HumanNote

    On POST /notes: a note that dismisses an INCORRECT finding MUST carry a
    `dismissal_reason`. Reject the request without one. It is what gives a
    reviewer an honest exit when the code is at fault rather than the
    document, and it is the cheapest labelled data this project will get.

    Read-only apart from notes. Applying a patch to a document is the human's
    job in phase 1; the system proposes and never writes.
    """
    raise NotImplementedError


def build_dashboard_context(run_id: str) -> dict[str, Any]:
    """Assemble the template context for a run page."""
    raise NotImplementedError
