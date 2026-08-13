/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   Mastery model — EXACT mirror of service/app/mastery.py (the source of
   truth). Both are tested against shared/mastery-fixtures.json; change one,
   change all three. */

export const REVIEW_DELTAS: Record<number, number> = { 1: -0.15, 2: 0.02, 3: 0.08, 4: 0.12 }

export const DECAY_HALF_LIFE_DAYS = 90

export function clamp01(x: number): number {
  return x < 0 ? 0 : x > 1 ? 1 : x
}

/** Concept score update from one parsing-card review. */
export function applyReview(score: number, rating: number): number {
  return clamp01(score + (REVIEW_DELTAS[rating] ?? 0))
}

/** Gentle time decay: half-life 90 days. */
export function applyDecay(score: number, days: number): number {
  if (days <= 0) return score
  return clamp01(score * 0.5 ** (days / DECAY_HALF_LIFE_DAYS))
}

export type DeckMasteryStats = { all_review: boolean; retention: number | null }

/** Mastered = every deck fully at review state with retention >= threshold,
 *  AND every concept >= threshold. No decks → never mastered by data. */
export function lessonMastered(
  deckStats: DeckMasteryStats[],
  conceptScores: number[],
  retentionThreshold = 0.9,
  conceptThreshold = 0.8,
): boolean {
  if (deckStats.length === 0) return false
  for (const deck of deckStats) {
    if (!deck.all_review) return false
    if ((deck.retention ?? 0) < retentionThreshold) return false
  }
  for (const score of conceptScores) {
    if (score < conceptThreshold) return false
  }
  return true
}
