"""Headless pipeline runner.

  python -m app.gen.run vocab --rank-from 1 --rank-to 40 --deck "GNT Vocab 1-40"
  python -m app.gen.run parsing --book John --chapter 1 --parse-like "V- _PAI%" \
      --max-cards 25 --deck "John 1 parsing"

Run via scripts\\generate.cmd (sets PYTHONUTF8=1 and PYTHONPATH).
"""

from __future__ import annotations

import argparse
import json

import anyio

from .. import db
from . import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.gen.run")
    sub = parser.add_subparsers(dest="kind", required=True)

    v = sub.add_parser("vocab")
    v.add_argument("--rank-from", type=int, required=True)
    v.add_argument("--rank-to", type=int, required=True)
    v.add_argument("--deck")

    p = sub.add_parser("parsing")
    p.add_argument("--book", required=True)
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--parse-like", required=True, help="SQL LIKE over parse, e.g. 'V- _PAI%%'")
    p.add_argument("--max-cards", type=int, default=25)
    p.add_argument("--deck")

    args = parser.parse_args()
    if args.kind == "vocab":
        spec = {"kind": "vocab", "rank_from": args.rank_from, "rank_to": args.rank_to}
    else:
        spec = {
            "kind": "parsing",
            "book": args.book,
            "chapter": args.chapter,
            "parse_like": args.parse_like,
            "max_cards": args.max_cards,
        }
    if args.deck:
        spec["deck"] = args.deck

    db.bootstrap()
    result = anyio.run(pipeline.run_batch, spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
