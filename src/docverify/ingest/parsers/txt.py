"""Plain text -> canonical plain text.

The trivial parser, and the reference for what "canonical" means: decode as
UTF-8 with a latin-1 fallback, normalise line endings to \\n, strip a BOM,
change nothing else. Do not reflow, do not collapse blank lines: the
segmenter uses blank lines as paragraph boundaries.
"""

from __future__ import annotations


def parse(data: bytes) -> tuple[str, dict[str, str]]:
    raise NotImplementedError
