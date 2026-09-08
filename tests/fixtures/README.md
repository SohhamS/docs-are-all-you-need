# Fixtures

`sample_doc.md` is paired with the fake repository in `tests/conftest.py`.
The pairing is deliberate, so an end-to-end test has real outcomes of each
kind to find:

| Statement in the document | Code says | Expected |
|---|---|---|
| default request timeout is 30 seconds | `30 * time.Second` | correct |
| client retries up to 3 times | `MaxRetries: 5` | **incorrect** |
| `list_items` returns 20 per page | `page_size: int = 20` | correct |
| maximum page size is 100 | `MAX_PAGE_SIZE = 100` | correct |
| "designed to be simple to reason about" | nothing can settle this | skipped (conceptual) |
| "Future releases may add more options" | nothing can settle this | skipped (conceptual) |
| "See the API reference..." | navigational | skipped |

Add a real product document here as soon as one is available. This one is
small enough to reason about by hand, which is useful for debugging and
useless for measuring quality.

## The labelled set

`tests/golden/` is for the SME-labelled claims. Until it exists, every prompt
change is a blind change: there is no way to tell whether a new version is
better or merely different. Building it is the highest-value hour available
on this project.

Format: one JSON file per source document, keyed by question text rather than
claim id, so ids can change without invalidating the labels.

    {
      "What is the default request timeout?": {
        "expected_verdict": "correct",
        "note": "Config.RequestTimeout defaults to 30s in DefaultConfig()"
      }
    }
