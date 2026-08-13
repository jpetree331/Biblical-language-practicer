import { useHashRoute } from './hooks/useHashRoute'
import { AboutPage } from './pages/AboutPage'
import { DeckPage } from './pages/DeckPage'
import { DecksPage } from './pages/DecksPage'
import { CorpusPage } from './pages/CorpusPage'
import { ImportPage } from './pages/ImportPage'
import { ReviewPage } from './pages/ReviewPage'

export default function App() {
  const route = useHashRoute()

  return (
    <>
      <nav className="app-nav">
        <a className="wordmark" href="#/decks">
          Scriptorium
        </a>
        <a href="#/decks">Decks</a>
        <a href="#/import">Import</a>
        <a href="#/corpus">Corpus</a>
        <a href="#/about">About</a>
      </nav>
      <main className="app-main">
        {route.page === 'decks' && <DecksPage />}
        {route.page === 'deck' && <DeckPage key={route.id} deckId={route.id} />}
        {route.page === 'review' && <ReviewPage key={route.id} deckId={route.id} />}
        {route.page === 'import' && <ImportPage />}
        {route.page === 'corpus' && <CorpusPage />}
        {route.page === 'about' && <AboutPage />}
      </main>
    </>
  )
}
