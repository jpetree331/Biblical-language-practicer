"""Mastery model — single source of truth, mirrored EXACTLY by
web/src/lib/mastery.ts. Both are tested against shared/mastery-fixtures.json;
change one, change all three.

Pure functions only: no DB, no clock — callers supply elapsed days.
"""

from __future__ import annotations

# rating (1-4, FSRS Again/Hard/Good/Easy) → concept-score delta
REVIEW_DELTAS = {1: -0.15, 2: 0.02, 3: 0.08, 4: 0.12}

DECAY_HALF_LIFE_DAYS = 90.0


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def apply_review(score: float, rating: int) -> float:
    """Concept score update from one parsing-card review (or checker result
    mapped onto the same 1-4 scale)."""
    return clamp01(score + REVIEW_DELTAS.get(rating, 0.0))


def apply_decay(score: float, days: float) -> float:
    """Gentle time decay: half-life 90 days."""
    if days <= 0:
        return score
    return clamp01(score * 0.5 ** (days / DECAY_HALF_LIFE_DAYS))


def lesson_mastered(
    deck_stats: list[dict],
    concept_scores: list[float],
    retention_threshold: float = 0.9,
    concept_threshold: float = 0.8,
) -> bool:
    """A lesson is mastered when every one of its decks has all cards at FSRS
    review state with retention >= threshold, AND every one of its concepts
    scores >= threshold. A lesson with no decks can't be mastered by data
    (use the manual override — Jess outranks the model of her own mastery)."""
    if not deck_stats:
        return False
    for deck in deck_stats:
        if not deck.get("all_review"):
            return False
        if (deck.get("retention") or 0.0) < retention_threshold:
            return False
    for score in concept_scores:
        if score < concept_threshold:
            return False
    return True
