import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { Deck } from '../api'
import { cardType } from '../config/cardTypes'
import { navigate } from '../hooks/useHashRoute'

type QueueEntry = {
  id: string
  deck_id: string
  card_type: string
  payload: Record<string, unknown>
  state: string
  reps: number
  due: string
}

type Queue = {
  queue: QueueEntry[]
  counts: { due: number; new: number; new_budget_left_today: number }
}

const RATING_LABELS = ['Again', 'Hard', 'Good', 'Easy']

/** Drill loop. Space = reveal, 1–4 = grade (Divergence Rule 3: pure
 *  SQLite + FSRS — nothing here ever calls a model). */
export function ReviewPage({ deckId }: { deckId: string }) {
  const [deck, setDeck] = useState<Deck | null>(null)
  const [queue, setQueue] = useState<QueueEntry[] | null>(null)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tally, setTally] = useState({ reviewed: 0, again: 0, streak: 0, bestStreak: 0 })

  useEffect(() => {
    api.get<Deck>(`/api/decks/${deckId}`).then(setDeck).catch((e) => setError(String(e)))
    api
      .get<Queue>(`/api/review/queue?deck_id=${deckId}`)
      .then((q) => setQueue(q.queue))
      .catch((e) => setError(String(e)))
  }, [deckId])

  const current = queue && index < queue.length ? queue[index] : null

  const grade = useCallback(
    async (rating: number) => {
      if (!current || busy) return
      setBusy(true)
      try {
        await api.post('/api/review/grade', { card_id: current.id, rating })
        setTally((t) => {
          const again = rating === 1
          const streak = again ? 0 : t.streak + 1
          return {
            reviewed: t.reviewed + 1,
            again: t.again + (again ? 1 : 0),
            streak,
            bestStreak: Math.max(t.bestStreak, streak),
          }
        })
        setRevealed(false)
        setIndex((i) => i + 1)
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setBusy(false)
      }
    },
    [current, busy],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === ' ') {
        e.preventDefault()
        setRevealed(true)
      } else if (revealed && ['1', '2', '3', '4'].includes(e.key)) {
        void grade(Number(e.key))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [revealed, grade])

  if (error) return <p className="form-error">{error}</p>
  if (!queue || !deck) return <p className="muted">Loading…</p>

  if (!current) {
    return (
      <div className="review-shell">
        <h1>{queue.length === 0 ? 'Nothing due' : 'Session complete'}</h1>
        {tally.reviewed > 0 ? (
          <div className="card-surface session-summary">
            <p>
              <strong>{tally.reviewed}</strong> reviewed · <strong>{tally.again}</strong> again ·
              best streak <strong>{tally.bestStreak}</strong>
            </p>
          </div>
        ) : (
          <p className="muted">This deck has no cards due and no new-card budget left today.</p>
        )}
        <p>
          <a href={`#/deck/${deckId}`}>← Back to {deck.name}</a>
        </p>
      </div>
    )
  }

  const spec = cardType(current.card_type)
  const variant = current.reps % spec.variantCount(current.payload)
  const ctx = { reps: current.reps }

  return (
    <div className="review-shell">
      <p className="muted">
        {deck.name} — {index + 1} / {queue.length}
        {current.state === 'new' ? ' · new card' : ''}
      </p>
      <div className="card-surface review-card">
        <div className="review-face">{spec.renderFront(current.payload, variant, ctx)}</div>
        {revealed && (
          <>
            <hr className="review-divider" />
            <div className="review-face">{spec.renderBack(current.payload, variant, ctx)}</div>
          </>
        )}
      </div>
      {revealed ? (
        <div className="grade-row">
          {RATING_LABELS.map((label, i) => (
            <button
              key={label}
              className={`grade grade-${i + 1}`}
              disabled={busy}
              onClick={() => grade(i + 1)}
            >
              {label} <span className="muted">{i + 1}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="grade-row">
          <button className="primary reveal" onClick={() => setRevealed(true)}>
            Reveal <span className="key-hint">space</span>
          </button>
        </div>
      )}
      <p className="muted center">
        <a href={`#/deck/${deckId}`} onClick={() => navigate(`/deck/${deckId}`)}>
          end session
        </a>
      </p>
    </div>
  )
}
