"""claude-agent-sdk wrapper for the generation pipeline.

Divergence Rule 5, enforced in code: if ANTHROPIC_API_KEY is present we refuse
to run — the SDK would silently bill API credits instead of the Max plan.
Subscription auth comes from the `claude` CLI login on this machine.

GATE A (defaults accepted 2026-08-13): claude-sonnet-5 generates,
claude-opus-5 verifies — a genuinely different model checks the generator's
work, mirroring the build/verify split.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

GENERATOR_MODEL = "claude-sonnet-5"
VERIFIER_MODEL = "claude-opus-5"


def assert_subscription_auth() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is set — refusing to run. The Agent SDK would "
            "bill API credits instead of the Max plan (Divergence Rule 5). "
            "Unset it and rely on `claude` CLI login."
        )


async def ask(model: str, system: str, prompt: str) -> tuple[str, dict]:
    """One single-turn, no-tools model call. Returns (text, usage_meta)."""
    assert_subscription_auth()
    # max_turns is a safety cap, not an expectation — no tools are allowed, but
    # a model can occasionally consume an extra internal turn before finishing.
    opts = ClaudeAgentOptions(
        model=model, max_turns=4, allowed_tools=[], system_prompt=system
    )
    text = ""
    meta: dict = {"model": model}
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, ResultMessage):
            text = msg.result or ""
            usage = getattr(msg, "usage", None) or {}
            meta["input_tokens"] = usage.get("input_tokens")
            meta["output_tokens"] = usage.get("output_tokens")
    return text, meta


def extract_json(text: str) -> Any:
    """Parse the first JSON value in model output, tolerating ```json fences,
    leading prose, and trailing commentary."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    starts = [i for i in (cleaned.find("["), cleaned.find("{")) if i != -1]
    if not starts:
        raise ValueError(f"no JSON found in model output: {text[:200]!r}")
    value, _end = json.JSONDecoder().raw_decode(cleaned[min(starts):])
    return value
