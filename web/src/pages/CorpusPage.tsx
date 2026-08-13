import { useEffect, useState } from 'react'
import { api } from '../api'

/* Corpus browser — a dev tool, deliberately unpolished (per plan).
   Pick a verse, see its tokens with lemma + parse. */

type Token = {
  id: number
  pos: number
  surface: string
  normalized: string
  lemma: string
  parse: string
  gloss: string | null
}

type BookInfo = { book: string; chapters: number }

export function CorpusPage() {
  const [books, setBooks] = useState<BookInfo[]>([])
  const [book, setBook] = useState('John')
  const [chapter, setChapter] = useState(1)
  const [verse, setVerse] = useState(1)
  const [tokens, setTokens] = useState<Token[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lemmaHits, setLemmaHits] = useState<{ lemma: string; total: number } | null>(null)

  useEffect(() => {
    api.get<BookInfo[]>('/api/corpus/books').then(setBooks).catch((e) => setError(String(e)))
  }, [])

  const lookup = async (b = book, c = chapter, v = verse) => {
    setError(null)
    setLemmaHits(null)
    try {
      const r = await api.get<{ tokens: Token[] }>(`/api/corpus/ref/${b}.${c}.${v}`)
      setTokens(r.tokens)
    } catch (e) {
      setTokens(null)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const lemmaInfo = async (lemma: string) => {
    const r = await api.get<{ lemma: string; total: number }>(
      `/api/corpus/lemma/${encodeURIComponent(lemma)}?limit=1`,
    )
    setLemmaHits({ lemma: r.lemma, total: r.total })
  }

  useEffect(() => {
    void lookup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <h1>Corpus browser</h1>
      <p className="muted">MorphGNT SBLGNT · dev tool</p>
      <div className="corpus-controls">
        <select value={book} onChange={(e) => setBook(e.target.value)}>
          {(books.length ? books : [{ book: 'John', chapters: 21 }]).map((b) => (
            <option key={b.book} value={b.book}>
              {b.book}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          value={chapter}
          onChange={(e) => setChapter(Number(e.target.value))}
          style={{ width: 70 }}
        />
        <input
          type="number"
          min={1}
          value={verse}
          onChange={(e) => setVerse(Number(e.target.value))}
          style={{ width: 70 }}
        />
        <button className="primary" onClick={() => void lookup()}>
          Look up
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}
      {lemmaHits && (
        <p className="muted">
          {lemmaHits.lemma}: {lemmaHits.total} occurrences in the GNT
        </p>
      )}

      {tokens && (
        <>
          <p className="greek">
            {book} {chapter}:{verse} — {tokens.map((t) => t.surface).join(' ')}
          </p>
          <table className="corpus-table">
            <thead>
              <tr>
                <th>#</th>
                <th>surface</th>
                <th>lemma</th>
                <th>parse</th>
                <th>gloss</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((t) => (
                <tr key={t.id}>
                  <td className="muted">{t.pos}</td>
                  <td className="greek-inline">{t.surface}</td>
                  <td className="greek-inline">
                    <button className="linklike" onClick={() => void lemmaInfo(t.lemma)}>
                      {t.lemma}
                    </button>
                  </td>
                  <td>
                    <code>{t.parse}</code>
                  </td>
                  <td className="muted">{t.gloss ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
