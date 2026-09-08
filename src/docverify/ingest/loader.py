"""Ingest entry point: a file on disk becomes a `NormalizedDoc`.

Every input format is converted here and nothing downstream ever sees the
original file. One internal representation means the pipeline, the coverage
arithmetic and the UI all deal with a single shape, and adding a format later
touches exactly one directory. See ADR 0005.

The visualization tab renders this normalized text with highlights. It does
not reproduce the original PDF or Word layout, which would need text-layer
coordinate work for a benefit nobody asked for.
"""

from __future__ import annotations

from pathlib import Path

from docverify.config import IngestConfig
from docverify.models import DocFormat, NormalizedDoc


class IngestError(Exception):
    """A document could not be ingested. The message is shown to the operator,
    so it must say what is wrong with the file and what to do about it."""


class ScannedPdfError(IngestError):
    """A PDF with no usable text layer.

    Rejected rather than OCR'd in phase 1. Generating claims from garbage text
    is worse than refusing the file: the claims look plausible, the verdicts
    look authoritative, and nobody can tell from the dashboard that the input
    was noise.
    """


class UnsupportedFormatError(IngestError):
    pass


def detect_format(path: Path) -> DocFormat:
    """Determine the format from the file extension.

    Extension only, deliberately. Sniffing content invites a .txt of HTML
    being parsed as HTML, which changes the offsets and therefore the
    highlighting, in a way the operator did not ask for.
    """
    raise NotImplementedError


def load(path: Path, run_id: str, cfg: IngestConfig) -> NormalizedDoc:
    """Load one file and return a segmented `NormalizedDoc`.

    Steps, in order:
      1. Check the size against `cfg.max_file_mb`.
      2. Detect format; reject if not in `cfg.accept_formats`.
      3. Hash the raw bytes into `source_sha256`. This is the identity of the
         document and part of every claim id derived from it.
      4. Dispatch to the parser for that format, which returns canonical text.
      5. Reject scanned PDFs per `cfg.reject_scanned_pdf`.
      6. Segment via `ingest.segment.segment`.
      7. Verify the tiling property with `assert_partition`.

    Raises:
        IngestError: with an operator-readable message.
    """
    raise NotImplementedError
