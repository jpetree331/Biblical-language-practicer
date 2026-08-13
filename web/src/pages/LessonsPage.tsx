import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../hooks/useHashRoute'

type Lesson = {
  id: string
  seq: number
  title: string
  chapter_ref: string | null
  status: 'locked' | 'active' | 'mastered'
  due: number
  decks_built: boolean
}

/** The spiral, visible: mastered lessons keep live due-counts forever;
 *  the active lesson is where new work happens; locked lessons wait. */
export function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.get<Lesson[]>('/api/lessons').then(setLessons).catch((e) => setError(String(e)))
  }, [])
  useEffect(load, [load])

  if (error) return <p className="form-error">{error}</p>
  if (!lessons) return <p className="muted">Loading…</p>
  if (lessons.length === 0)
    return (
      <div>
        <h1>Lessons</h1>
        <p className="muted">
          No curriculum loaded yet — run <code>scripts\load-syllabus.cmd</code> after the
          syllabus map exists.
        </p>
      </div>
    )

  return (
    <div>
      <h1>Lessons</h1>
      <ul className="lesson-list">
        {lessons.map((l) => (
          <li key={l.id} className={`lesson-row lesson-${l.status}`}>
            <button
              className="lesson-main"
              disabled={l.status === 'locked'}
              onClick={() => navigate(`/lesson/${l.id}`)}
            >
              <span className="lesson-seq">{l.seq}</span>
              <span className="lesson-title">{l.title}</span>
              <span className={`lesson-status lesson-status-${l.status}`}>
                {l.status === 'mastered' && l.due > 0 ? `${l.due} due` : l.status}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
