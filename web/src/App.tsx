import { useEffect, useState } from 'react'

type Health = { ok: boolean; db: string; version: string }

/** Sprint 0 skeleton: health check + polytonic Greek render proof.
 *  Replaced by real routing in Sprint 1. */
export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 'var(--sp-6)' }}>
      <h1>Scriptorium</h1>
      <p className="muted">A spiral-method flashcard engine, and a Greek tutor growing inside it.</p>

      <section className="card-surface" style={{ marginBottom: 'var(--sp-5)' }}>
        <h2>Service</h2>
        {health ? (
          <p>
            {health.ok ? 'Healthy' : 'Database problem'} — v{health.version}
            <br />
            <span className="muted">{health.db}</span>
          </p>
        ) : error ? (
          <p>Service unreachable: {error}</p>
        ) : (
          <p className="muted">Checking…</p>
        )}
      </section>

      <section className="card-surface">
        <h2>Polytonic proof</h2>
        <p className="greek">ἐν ἀρχῇ ἦν ὁ λόγος, ᾧ ῥῆμα</p>
        <p className="muted">
          If the breathings, iota subscript, and circumflexes above render cleanly, the Greek
          font stack is sound.
        </p>
      </section>
    </main>
  )
}
