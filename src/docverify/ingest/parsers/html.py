"""HTML -> canonical plain text.

- Drop script, style, nav, header and footer elements before extracting.
- Preserve block structure as blank lines so the segmenter can find
  paragraphs.
- Preserve <pre> and <code> verbatim.
- Flatten tables to one row per line, cells tab-separated.
- Capture <title> into metadata.

Use BeautifulSoup with lxml. Regex-stripping tags loses the block structure
the segmenter depends on.
"""

from __future__ import annotations


def parse(data: bytes) -> tuple[str, dict[str, str]]:
    raise NotImplementedError
