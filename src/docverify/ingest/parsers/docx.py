"""Word .docx -> canonical plain text.

- Paragraphs in document order, separated by a blank line.
- Heading styles become markdown-style heading markers so the segmenter can
  build `heading_path` the same way it does for markdown.
- Tables flattened to one row per line, cells tab-separated.
- Capture core properties (title, author) into metadata.
- Skip headers, footers and comments: they are not the document's claims.

Use python-docx.
"""

from __future__ import annotations


def parse(data: bytes) -> tuple[str, dict[str, str]]:
    raise NotImplementedError
