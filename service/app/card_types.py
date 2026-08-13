"""Card-type registry, backend side.

Divergence Rule 1: components and endpoints never branch on card type.
Adding a card type = adding an entry here (and its twin in
web/src/config/cardTypes.ts). Each entry carries a JSON Schema for its
payload plus an optional extra structural check.
"""

from __future__ import annotations

from typing import Any, Callable

import jsonschema


def _check_cloze(payload: dict) -> list[str]:
    """Deletions must be in-range, ordered, non-overlapping spans of text."""
    errors: list[str] = []
    text: str = payload["text"]
    prev_end = -1
    for i, d in enumerate(payload["deletions"]):
        if d["start"] >= d["end"]:
            errors.append(f"deletion {i}: start must be < end")
        elif d["end"] > len(text):
            errors.append(f"deletion {i}: end {d['end']} past end of text ({len(text)})")
        elif d["start"] < prev_end:
            errors.append(f"deletion {i}: overlaps previous deletion")
        prev_end = max(prev_end, d["end"])
    if not payload["deletions"]:
        errors.append("cloze needs at least one deletion")
    return errors


REGISTRY: dict[str, dict[str, Any]] = {
    "basic": {
        "schema": {
            "type": "object",
            "properties": {
                "front": {"type": "string", "minLength": 1},
                "back": {"type": "string", "minLength": 1},
                "hint": {"type": "string"},
            },
            "required": ["front", "back"],
            "additionalProperties": False,
        },
        "check": None,
    },
    "verse": {
        "schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "minLength": 1},
                "translation": {"type": "string"},
                "text": {"type": "string", "minLength": 1},
                "graduateAfter": {"type": "integer", "minimum": 0},
            },
            "required": ["reference", "text"],
            "additionalProperties": False,
        },
        "check": None,
    },
    "cloze": {
        "schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "deletions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer", "minimum": 0},
                            "end": {"type": "integer", "minimum": 1},
                        },
                        "required": ["start", "end"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["text", "deletions"],
            "additionalProperties": False,
        },
        "check": _check_cloze,
    },
}


def validate_payload(card_type: str, payload: Any) -> list[str]:
    """Return a list of human-readable problems; empty list = valid."""
    entry = REGISTRY.get(card_type)
    if entry is None:
        return [f"unknown card type '{card_type}'"]
    validator = jsonschema.Draft202012Validator(entry["schema"])
    errors = [e.message for e in validator.iter_errors(payload)]
    if errors:
        return errors
    check: Callable | None = entry["check"]
    return check(payload) if check else []
