"""Deterministic segmentation. No LLM anywhere in this file.

Splits a `NormalizedDoc.text` into `Unit`s that form a COMPLETE,
NON-OVERLAPPING, ORDERED partition of the document. Completeness is the whole
point: it is what makes coverage arithmetic instead of a model's opinion, and
what lets the visualization tab colour every character.

Two properties the implementation must guarantee, and which
`tests/test_ingest.py` asserts:

    units[0].span.start == 0
    units[-1].span.end == len(doc.text)
    units[i].span.end == units[i + 1].span.start

Offsets originate here and only here. A model is never asked to produce or
adjust one; it works with unit ids. Models are unreliable at character
arithmetic in a way that is easy to miss and expensive to debug, and there is
no reason to find out where the limit is. See ADR 0002.

IMPLEMENTATION NOTES
--------------------
- Split on structure first (headings, paragraphs, list items, table rows,
  code blocks), then split paragraph text into sentences.
- Sentence splitting must not break on "e.g.", "i.e.", "v1.2.3", "Fig. 4" or
  a decimal number. A small abbreviation list beats a clever regex.
- A fenced code block is ONE unit. Never split inside it.
- Whitespace between units belongs to the preceding unit, so the partition
  stays gapless.
- Keep `heading_path` accurate. It is the only document context the
  investigator gets, and getting it wrong makes questions unanswerable.
"""

from __future__ import annotations

from docverify.models import NormalizedDoc, Unit


def segment(doc: NormalizedDoc) -> list[Unit]:
    """Split a document into a complete ordered partition of units.

    Args:
        doc: A normalized document with `text` populated and `units` empty.

    Returns:
        Units in document order, tiling `doc.text` completely.

    Raises:
        ValueError: if the resulting units would not tile the text.
    """
    raise NotImplementedError


def assert_partition(text: str, units: list[Unit]) -> None:
    """Verify the tiling property. Call this at the end of `segment`.

    Cheap, and it turns a class of silent coverage bugs into a loud failure
    at the point they are introduced.
    """
    if not units:
        if text:
            raise ValueError("no units produced for non-empty text")
        return
    if units[0].span.start != 0:
        raise ValueError(f"first unit starts at {units[0].span.start}, expected 0")
    if units[-1].span.end != len(text):
        raise ValueError(f"last unit ends at {units[-1].span.end}, expected {len(text)}")
    for a, b in zip(units[:-1], units[1:], strict=True):
        if a.span.end != b.span.start:
            raise ValueError(f"gap or overlap between units {a.id} and {b.id}")
        if a.ordinal + 1 != b.ordinal:
            raise ValueError(f"non-contiguous ordinals at {a.id}")
