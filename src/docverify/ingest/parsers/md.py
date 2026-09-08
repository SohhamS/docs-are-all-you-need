"""Markdown -> canonical plain text.

Every parser in this package has the same contract:

    parse(data: bytes) -> tuple[str, dict[str, str]]

returning the canonical text and a metadata dict. Offsets are computed later
by `ingest.segment` over the returned text, so what matters is that the text
is stable and readable, not that it preserves the original markup.

Markdown specifics:
- Keep fenced code blocks verbatim, fences included. The segmenter treats a
  fence as a single unit and the classifier needs to see it is code.
- Keep heading markers so the segmenter can build `heading_path`.
- Flatten tables to one row per line, cells separated by a tab.
"""

from __future__ import annotations


def parse(data: bytes) -> tuple[str, dict[str, str]]:
    raise NotImplementedError
