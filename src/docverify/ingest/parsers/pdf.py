"""PDF -> canonical plain text.

Use PyMuPDF (fitz). Extract per page, join pages with a blank line.

SCANNED PDFS
------------
Before returning, check extractable characters per page against
`IngestConfig.min_extractable_chars_per_page`. If a document falls below it,
raise `ScannedPdfError`. Phase 1 rejects rather than OCRs, because claims
generated from empty or garbled text still produce confident-looking verdicts
and nothing on the dashboard reveals the input was unusable.

Other notes:
- Strip repeated page headers and footers where they can be detected by
  recurrence at the same position across pages; leave them alone otherwise.
- De-hyphenate words broken across line breaks.
- Record page count and per-page character counts in metadata; the operator
  needs them to understand a rejection.
"""

from __future__ import annotations


def parse(data: bytes) -> tuple[str, dict[str, str]]:
    raise NotImplementedError
