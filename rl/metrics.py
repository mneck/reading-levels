from __future__ import annotations

import math
import re
from typing import Dict, Optional

# Optional dependency
try:
    import textstat  # type: ignore
except Exception:  # pragma: no cover
    textstat = None

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_RE = re.compile(r"[.!?]+")
_VOWEL_RE = re.compile(r"[aeiouy]+", re.I)


def _tokenize_words(text: str):
    return _WORD_RE.findall(text)


def _count_sentences(text: str) -> int:
    # crude but robust
    parts = _SENTENCE_RE.split(text)
    count = sum(1 for p in parts if p.strip())
    return max(1, count)


def _count_syllables_in_word(word: str) -> int:
    w = word.lower()
    # Remove trailing 'e' (silent e)
    if len(w) > 2 and w.endswith("e") and not w.endswith("le"):
        w = w[:-1]
    groups = _VOWEL_RE.findall(w)
    syllables = len(groups)
    return max(1, syllables)


def _count_syllables(words):
    return sum(_count_syllables_in_word(w) for w in words)


def _count_complex_words(words):
    # words with 3+ syllables
    complex_count = 0
    for w in words:
        if _count_syllables_in_word(w) >= 3:
            complex_count += 1
    return complex_count


def readability_metrics(text: str) -> Dict[str, Optional[float]]:
    text = text.strip()
    if not text:
        return {"gunning_fog": None, "dale_chall": None, "flesch_reading_ease": None,
                "num_words": 0, "num_sentences": 0}

    if textstat is not None:
        try:
            return {
                "gunning_fog": float(textstat.gunning_fog(text)),
                "dale_chall": float(textstat.dale_chall_readability_score(text)),
                "flesch_reading_ease": float(textstat.flesch_reading_ease(text)),
                "num_words": int(textstat.lexicon_count(text, removepunct=True)),
                "num_sentences": int(textstat.sentence_count(text)),
            }
        except Exception:
            # fall back to native impl
            pass

    words = _tokenize_words(text)
    num_words = len(words)
    num_sentences = _count_sentences(text)
    syllables = _count_syllables(words)
    complex_words = _count_complex_words(words)

    if num_words == 0:
        return {"gunning_fog": None, "dale_chall": None, "flesch_reading_ease": None,
                "num_words": 0, "num_sentences": num_sentences}

    # Flesch Reading Ease
    asl = num_words / max(1, num_sentences)
    asw = syllables / num_words
    flesch = 206.835 - 1.015 * asl - 84.6 * asw

    # Gunning Fog
    perc_complex = (complex_words / num_words) * 100.0
    gunning = 0.4 * (asl + perc_complex)

    # Dale–Chall (approximate without full easy-word list)
    # As an approximation, treat words <= 3 letters as "easy" and penalize long words.
    # If accuracy matters, install `textstat`.
    difficult = sum(1 for w in words if len(w) > 3)
    pdw = (difficult / num_words) * 100.0
    dale = 0.1579 * pdw + 0.0496 * asl
    if pdw > 5.0:
        dale += 3.6365

    return {
        "gunning_fog": gunning,
        "dale_chall": dale,
        "flesch_reading_ease": flesch,
        "num_words": num_words,
        "num_sentences": num_sentences,
    }
