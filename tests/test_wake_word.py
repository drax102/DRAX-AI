"""
test_wake_word.py — Unit tests for wake word scoring and matching.
"""

from backend.core.wake_word import _score_against_wake_words, _is_false_positive, _soundex, _phonetic_match


def test_soundex():
    assert _soundex("Drax") == "D620"
    assert _phonetic_match("hey drax", "hey dracs") is True


def test_wake_word_scoring():
    # Exact match
    assert _score_against_wake_words("hey drax") == 1.0
    assert _score_against_wake_words("drax") == 1.0

    # Token match
    assert _score_against_wake_words("hey dracs") >= 0.70


def test_false_positive_rejection():
    assert _is_false_positive("hello") is True
    assert _is_false_positive("hey google") is True
    assert _is_false_positive("hey drax") is False
