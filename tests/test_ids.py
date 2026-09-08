"""Identifier derivation.

Ids are content-derived so that re-ingesting an unchanged document does not
duplicate work and a resumed run still matches its stored stage outputs. If
these become non-deterministic, resume breaks in a way that looks like data
corruption.
"""

from __future__ import annotations

from docverify import ids


def test_claim_ids_are_stable() -> None:
    a = ids.claim_id("sha", "u_1", "What is the default timeout?")
    b = ids.claim_id("sha", "u_1", "What is the default timeout?")
    assert a == b


def test_claim_ids_ignore_question_casing_and_spacing() -> None:
    """Two phrasings of the same question are the same claim."""
    a = ids.claim_id("sha", "u_1", "What is the default timeout?")
    b = ids.claim_id("sha", "u_1", "  what is the default timeout  ")
    assert a == b


def test_claim_ids_differ_across_documents() -> None:
    a = ids.claim_id("sha_one", "u_1", "q")
    b = ids.claim_id("sha_two", "u_1", "q")
    assert a != b


def test_claim_ids_differ_across_questions() -> None:
    a = ids.claim_id("sha", "u_1", "how many retries?")
    b = ids.claim_id("sha", "u_1", "what backoff strategy?")
    assert a != b


def test_unit_ids_depend_on_position() -> None:
    a = ids.unit_id("sha", 0, 0, 10)
    b = ids.unit_id("sha", 1, 10, 20)
    assert a != b
    assert ids.unit_id("sha", 0, 0, 10) == a


def test_question_key_merges_equivalent_phrasings() -> None:
    """The dedupe key, unused in phase 1 but defined now so adopting it later
    needs no migration."""
    a = ids.question_key("What is the default timeout?")
    b = ids.question_key("  What is the default timeout  ")
    assert a == b


def test_question_key_is_case_insensitive_including_identifiers() -> None:
    """A known limitation, recorded so it is not rediscovered as a bug.

    Normalisation lowercases, so questions about `MaxRetries` and `maxretries`
    collapse to one key. Harmless in most codebases and wrong in one that
    distinguishes two identifiers only by case. It matters only once
    deduplication is switched on, which is a roadmap item; revisit the
    normaliser then rather than making it clever now.
    """
    assert ids.question_key("What is MAX_SIZE?") == ids.question_key("what is max_size")


def test_run_ids_are_unique() -> None:
    assert ids.new_run_id() != ids.new_run_id()


def test_sha_helpers_agree() -> None:
    assert ids.sha256_text("hello") == ids.sha256_bytes(b"hello")
