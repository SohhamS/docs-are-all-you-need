# 0005. One internal document representation

Status: accepted

## Context

Inputs are docx, pdf, html, md and txt, uploaded through a UI or the CLI. The
product shows the whole document with every span coloured by outcome.

## Decision

**Every format is converted at ingest to a single `NormalizedDoc`** with
canonical plain text and units carrying offsets into it. Nothing downstream
sees the original file.

**The visualization tab renders the normalized text**, not the original
layout.

**Scanned PDFs are rejected at ingest**, not OCR'd.

## Why one representation

The pipeline, the coverage arithmetic and the UI all deal with one shape.
Adding a format touches one directory. Without it, every stage would need to
know about five formats and the offsets would mean five different things.

## Why not the original layout

Highlighting arbitrary spans in a PDF needs text-layer coordinate work in
PDF.js, and in a docx it needs a rendering engine. That is substantial effort
for a benefit nobody asked for: reviewers need to read the text and see which
parts are flagged, which clean text plus highlights delivers.

If original-layout rendering is ever wanted, it is a phase 2 UI feature that
does not touch the pipeline, because the offsets are already stored.

## Why reject scanned PDFs

A PDF with no text layer extracts to empty or garbled text. Claims generated
from it look plausible, verdicts on them look authoritative, and nothing on
the dashboard reveals the input was noise. Refusing the file with a clear
message is the honest failure.

If OCR is added later, documents must be marked OCR-derived and that must
surface on every claim from them.

## Consequences

- Parser quality directly determines segmentation quality, which determines
  coverage. Parsers deserve real tests.
- The UI cannot show a page number for a PDF claim unless the parser records
  page boundaries in metadata. Worth doing in the PDF parser.
- Documents are stored twice in effect: original bytes hashed for identity,
  normalized text stored for the pipeline and the UI.
