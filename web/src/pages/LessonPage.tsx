import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { navigate } from '../hooks/useHashRoute'

type Concept = { id: string; name: string; score: number }

type Item = {
  id: string
  kind: 'read' | 'drill' | 'translate' | 'compose'
  ref: string
  seq: number
  read?: { title: string; body?: string; pointer?: string; in_app: boolean }
  deck?: {
    id: string
    name: string
    due: number
    new: number
    total: number
    all_review: boolean
    retention: number | null
  } | null
  pending?: boolean
}

type Lesson = {
  id: string
  seq: number
  title: string
  status: 'locked' | 'active' | 'mastered'
  items: Item[]
  concepts: Concept[]
}

export function LessonPage({ lessonId }: { lessonId: string }) {
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [readingOpen, setReadingOpen] = useState(false)

  const load = useCallback(() => {
    api.get<Lesson>(`/api/lessons/${lessonId}`).then(setLesson).catch((e) => setError(String(e)))
  }, [lessonId])
  useEffect(load, [load])

  const override = async (status: 'locked' | 'active' | 'mastered') => {
    await api.post(`/api/lessons/${lessonId}/status`, { status })
    load()
  }

  if (error) return <p className="form-error">{error}</p>
  if (!lesson) return <p className="muted">Loading…</p>

  return (
    <div>
      <p>
        <a href="#/lessons">← All lessons</a>
      </p>
      <div className="page-head">
        <h1>
          {lesson.seq}. {lesson.title}
        </h1>
        <span className={`lesson-status lesson-status-${lesson.status}`}>{lesson.status}</span>
      </div>

      <div className="head-actions" style={{ marginBottom: 'var(--sp-5)' }}>
        {lesson.status !== 'mastered' && (
          <button onClick={() => override('mastered')}>Force-master</button>
        )}
        {lesson.status !== 'active' && (
          <button onClick={() => override('active')}>Force-unlock</button>
        )}
        {lesson.status !== 'locked' && <button onClick={() => override('locked')}>Re-lock</button>}
      </div>

      <ol className="item-list">
        {lesson.items.map((item) => (
          <li key={item.id} className="item-row card-surface">
            {item.kind === 'read' && item.read && (
              <div>
                <div className="item-kind">Read</div>
                {item.read.in_app ? (
                  <>
                    <button className="linklike" onClick={() => setReadingOpen((o) => !o)}>
                      {readingOpen ? 'Hide' : 'Read'} “{item.read.title}” (Machen)
                    </button>
                    {readingOpen && <pre className="reading-body">{item.read.body}</pre>}
                  </>
                ) : (
                  <p>{item.read.pointer}</p>
                )}
              </div>
            )}
            {item.kind === 'drill' && (
              <div>
                <div className="item-kind">Drill</div>
                {item.deck ? (
                  <div className="drill-line">
                    <span>{item.deck.name}</span>
                    <span className="muted">
                      {item.deck.due} due · {item.deck.new} new ·{' '}
                      {item.deck.retention != null
                        ? `${Math.round(item.deck.retention * 100)}% retention`
                        : 'no retention yet'}
                    </span>
                    <button className="primary" onClick={() => navigate(`/review/${item.deck!.id}`)}>
                      Review
                    </button>
                  </div>
                ) : (
                  <p className="muted">
                    Deck not built yet — <code>scripts\build-chapter.cmd greek {lesson.seq}</code>
                  </p>
                )}
              </div>
            )}
            {(item.kind === 'translate' || item.kind === 'compose') && (
              <div>
                <div className="item-kind">{item.kind === 'translate' ? 'Translate' : 'Compose'}</div>
                <p className="muted">arrives with {item.kind === 'translate' ? 'Sprint 8' : 'Sprint 9'}</p>
              </div>
            )}
          </li>
        ))}
      </ol>

      {lesson.concepts.length > 0 && (
        <section style={{ marginTop: 'var(--sp-5)' }}>
          <h2>Concepts</h2>
          <ul className="concept-list">
            {lesson.concepts.map((c) => (
              <li key={c.id}>
                <span>{c.name}</span>
                <span className="concept-bar">
                  <span
                    className={`concept-fill ${c.score >= 0.8 ? 'good' : c.score >= 0.4 ? 'warm' : ''}`}
                    style={{ width: `${Math.round(c.score * 100)}%` }}
                  />
                </span>
                <span className="muted">{Math.round(c.score * 100)}%</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
