"""SQLite connection + idempotent schema bootstrap.

Single local DB at <repo>/data/scriptorium.db, WAL mode, Row factory.
Raw SQL throughout — no ORM (locked decision).
"""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "scriptorium.db"

SCHEMA = """
create table if not exists decks (
  id text primary key,
  name text not null,
  topic text not null default 'general',
  config text not null default '{}',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  deleted_at text
);

create table if not exists cards (
  id text primary key,
  deck_id text not null references decks(id),
  card_type text not null,
  payload text not null,
  source text,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  deleted_at text
);

create table if not exists card_state (
  card_id text primary key references cards(id),
  stability real, difficulty real,
  due text not null,
  last_review text,
  reps integer not null default 0,
  lapses integer not null default 0,
  state text not null default 'new'
);

create table if not exists review_log (
  id text primary key,
  card_id text not null references cards(id),
  rating integer not null,
  reviewed_at text not null default (datetime('now')),
  elapsed_days real, scheduled_days real
);

create table if not exists corpora (
  id text primary key, name text not null, license text not null
);

create table if not exists corpus_tokens (
  id integer primary key,
  corpus_id text not null references corpora(id),
  book text not null, chapter integer not null, verse integer not null,
  pos integer not null,
  surface text not null,
  normalized text not null,
  lemma text not null,
  parse text not null,
  gloss text
);
create index if not exists idx_corpus_tokens_ref
  on corpus_tokens (corpus_id, book, chapter, verse, pos);
create index if not exists idx_corpus_tokens_lemma
  on corpus_tokens (corpus_id, lemma);

create table if not exists lemma_freq (
  corpus_id text not null, lemma text not null,
  count integer not null, rank integer not null,
  primary key (corpus_id, lemma)
);

create table if not exists concepts (
  id text primary key,
  name text not null,
  chapter_ref text
);

create table if not exists lessons (
  id text primary key,
  seq integer not null unique,
  title text not null,
  chapter_ref text,
  status text not null default 'locked'
);

create table if not exists lesson_items (
  id text primary key,
  lesson_id text not null references lessons(id),
  kind text not null,
  ref text not null,
  seq integer not null
);

create table if not exists concept_mastery (
  concept_id text primary key references concepts(id),
  score real not null default 0,
  updated_at text not null default (datetime('now'))
);

create table if not exists exercises (
  id text primary key,
  lesson_id text references lessons(id),
  kind text not null,
  prompt text not null,
  answer_key text,
  created_at text not null default (datetime('now'))
);

create table if not exists submissions (
  id text primary key,
  exercise_id text not null references exercises(id),
  answer text not null,
  feedback text,
  score real,
  submitted_at text not null default (datetime('now'))
);

create table if not exists gen_batches (
  id text primary key,
  spec text not null,
  models text not null,
  generated integer not null default 0,
  validated integer not null default 0,
  verified integer not null default 0,
  landed integer not null default 0,
  started_at text not null default (datetime('now')),
  finished_at text
);
"""


def get_conn() -> sqlite3.Connection:
    """Open a connection with WAL mode and Row factory. Caller closes."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma journal_mode=wal")
    conn.execute("pragma foreign_keys=on")
    return conn


def bootstrap() -> None:
    """Idempotent schema creation; runs at service startup."""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def nfc(text: str) -> str:
    """All Greek (and everything else) is stored NFC-normalized."""
    return unicodedata.normalize("NFC", text)
