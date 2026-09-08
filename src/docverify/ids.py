"""Deterministic identifier derivation.

Ids are derived from content, not generated randomly, so that re-ingesting the
same document against the same commit produces the same ids. That gives
deduplication, resumability and cache keys for free.

The one exception is `new_run_id`, which is genuinely a new event each time.
"""

from __future__ import annotations

import hashlib
import re
import uuid

# A fixed namespace. Do not change it: every id in every existing database
# derives from it.
NAMESPACE = uuid.UUID("6f9b1a7e-1c2d-4c5b-9f3a-8d7e6c5b4a39")

_WHITESPACE = re.compile(r"\s+")


def sha256_text(text: str) -> str:
    """Hex sha256 of text, encoded UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Hex sha256 of raw bytes. Used for the source file digest."""
    return hashlib.sha256(data).hexdigest()


def normalize_question(question: str) -> str:
    """Canonical form of a question, for hashing and deduplication.

    Lowercased, whitespace collapsed, trailing punctuation stripped. Kept
    deliberately crude: this decides whether two questions are "the same", and
    a clever normaliser that merges genuinely different questions is worse
    than a dumb one that misses a few duplicates.
    """
    q = _WHITESPACE.sub(" ", question).strip().lower()
    return q.rstrip("?.! ")


def new_run_id() -> str:
    """A fresh run identifier."""
    return f"run_{uuid.uuid4().hex[:16]}"


def doc_id(run_id: str, source_sha256: str) -> str:
    """Identifier for a document within a run."""
    return f"doc_{uuid.uuid5(NAMESPACE, f'{run_id}:{source_sha256}').hex[:16]}"


def unit_id(doc_sha256: str, ordinal: int, start: int, end: int) -> str:
    """Identifier for a segmented unit.

    Derived from the document digest and the unit's position, so the same
    document always segments to the same unit ids.
    """
    key = f"{doc_sha256}:{ordinal}:{start}:{end}"
    return f"u_{uuid.uuid5(NAMESPACE, key).hex[:16]}"


def claim_id(doc_sha256: str, unit_id_: str, question: str) -> str:
    """Identifier for a claim.

    Derived from the document, the unit it came from and the normalized
    question. Re-running classification over an unchanged document yields the
    same claim ids, so nothing is duplicated and stored stage outputs still
    match.
    """
    key = f"{doc_sha256}:{unit_id_}:{normalize_question(question)}"
    return f"c_{uuid.uuid5(NAMESPACE, key).hex[:16]}"


def question_key(question: str) -> str:
    """Cache key for an investigation, independent of which claim asked.

    Two documents asking the same question should not be investigated twice,
    and must not receive contradictory answers. Deduplication by this key is
    a roadmap item rather than phase 1 behaviour; the key exists now so the
    later change does not require a schema migration.
    """
    return f"q_{uuid.uuid5(NAMESPACE, normalize_question(question)).hex[:16]}"
