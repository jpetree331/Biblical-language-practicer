import { useEffect, useState } from 'react'
import { api } from '../api'
import { decodeParse } from '../lib/parseCode'
import { translit } from '../lib/translit'

type Token = {
  id: number
  pos: number
  surface: string
  lemma: string
  parse: string
  gloss: string | null
  known?: boolean
}

type Exercise = {
  id: string
  kind: 'translate_gk_en' | 'compose'
  lesson_id: string | null
  prompt: {
    ref?: string
    tokens?: Token[]
    english?: string
  }
}

type Note = {
  token_id: number
  kind: 'error' | 'nitpick' | 'praise'
  note: string
  surface: string
  checked_against: string
}

type Feedback = {
  submission_id: string
  score: number | null
  summary: string
  notes: Note[]
  withheld_count: number
}

export function ExercisePage({ exerciseId }: { exerciseId: string }) {
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [tapped, setTapped] = useState<Token | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .get<Exercise>(`/api/exercises/${exerciseId}`)
      .then(setExercise)
      .catch((e) => setError(String(e)))
  }, [exerciseId])

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const payload = exercise?.kind === 'compose' ? translit(answer) : answer
      setFeedback(await api.post<Feedback>(`/api/exercises/${exerciseId}/submit`, { answer: payload }))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  if (error && !exercise) return <p className="form-error">{error}</p>
  if (!exercise) return <p className="muted">Loading…</p>

  const isCompose = exercise.kind === 'compose'

  return (
    <div className="review-shell">
      {exercise.lesson_id && (
        <p>
          <a href={`#/lesson/${exercise.lesson_id}`}>← Back to lesson</a>
        </p>
      )}
      <h1>{isCompose ? 'Compose in Greek' : 'Translate'}</h1>

      {!isCompose && exercise.prompt.tokens && (
        <div className="card-surface" style={{ marginBottom: 'var(--sp-4)' }}>
          <p className="muted">{exercise.prompt.ref?.replaceAll('.', ' ')} — tap a word for its parsing</p>
          <p className="greek passage">
            {exercise.prompt.tokens.map((t) => (
              <button
                key={t.id}
                className={`token ${tapped?.id === t.id ? 'token-active' : ''}`}
                onClick={() => setTapped(tapped?.id === t.id ? null : t)}
              >
                {t.surface}
              </button>
            ))}
          </p>
          {tapped && (
            <p className="muted token-info">
              <span className="greek-inline">{tapped.lemma}</span> · {decodeParse(tapped.parse)}
              {tapped.gloss ? ` · “${tapped.gloss}”` : ''}{' '}
              <span className="footnote">from MorphGNT — no model involved</span>
            </p>
          )}
        </div>
      )}

      {isCompose && (
        <div className="card-surface" style={{ marginBottom: 'var(--sp-4)' }}>
          <p>{exercise.prompt.english}</p>
          <p className="muted">
            Type Latin, get Greek: <code>lo/gos</code> → λόγος · breathings <code>)a (a</code> ·
            accents <code>a/ a\ a=</code> · iota subscript <code>a|</code>
          </p>
        </div>
      )}

      {!feedback && (
        <>
          <textarea
            rows={3}
            value={answer}
            placeholder={isCompose ? ')en )arch=| ...' : 'Your English translation…'}
            onChange={(e) => setAnswer(e.target.value)}
            style={{ width: '100%', marginBottom: 'var(--sp-2)' }}
          />
          {isCompose && answer && (
            <p className="greek compose-preview" aria-live="polite">
              {translit(answer)}
            </p>
          )}
          {error && <p className="form-error">{error}</p>}
          <div className="actions">
            <button className="primary" onClick={submit} disabled={busy || !answer.trim()}>
              {busy ? 'Checking…' : 'Submit'}
            </button>
          </div>
        </>
      )}

      {feedback && (
        <div className="card-surface">
          <h2>
            {feedback.score != null ? `${Math.round(feedback.score * 100)}%` : 'Checked'}
          </h2>
          <p>{feedback.summary}</p>
          {isCompose ? (
            <p className="greek">{translit(answer)}</p>
          ) : (
            <p>{answer}</p>
          )}
          {feedback.notes.length > 0 && (
            <ul className="note-list">
              {feedback.notes.map((n, i) => (
                <li key={i} className={`note note-${n.kind}`}>
                  <span className="greek-inline">{n.surface}</span> — {n.note}
                  <span className="footnote"> checked against {n.checked_against}</span>
                </li>
              ))}
            </ul>
          )}
          {feedback.withheld_count > 0 && (
            <p className="muted">
              {feedback.withheld_count} note{feedback.withheld_count === 1 ? ' was' : 's were'}{' '}
              withheld (failed citation verification).
            </p>
          )}
          <div className="actions">
            <button
              onClick={() => {
                setFeedback(null)
                setAnswer('')
              }}
            >
              Try again
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
