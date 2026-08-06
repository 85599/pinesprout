"""Generate Pine Script source from a natural-language prompt.

Uses the Anthropic Messages API when ``ANTHROPIC_API_KEY`` is configured.
The generated code is always re-validated with PineSprout's own linter and
version-detector before being returned, so callers get a
:class:`GenerationResult` with lint feedback attached rather than a bare
string that might be broken.
"""

from __future__ import annotations

import json
import os
import re

import httpx
from pydantic import BaseModel

from pinesprout.core.linter import Linter, LintIssue
from pinesprout.core.upgrader import detect_version

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are an expert TradingView Pine Script (v6) developer.
Given a natural-language request, write a single, complete, compilable
Pine Script file that satisfies it.

Rules:
- Always start with a `//@version=6` pragma unless the user explicitly
  asks for a different version.
- Always include a valid `indicator(...)`, `strategy(...)`, or
  `library(...)` declaration.
- Prefer built-ins from the `ta.*`, `math.*`, `request.*`, `str.*`
  namespaces (v5/v6 style); never use deprecated v4 global functions like
  `study()`, bare `rsi()`, `sma()`, `security()`, etc.
- Use `input.*()` for any user-tunable parameter.
- Add concise `//` comments explaining non-obvious logic.
- Return ONLY the Pine Script code in a single fenced code block
  (```pine ... ```). Do not include any explanation outside the block.
"""


class GenerationRequest(BaseModel):
    prompt: str
    script_type: str = "indicator"  # indicator | strategy | library
    pine_version: int = 6
    model: str = DEFAULT_MODEL
    max_tokens: int = 4096


class GenerationResult(BaseModel):
    prompt: str
    source: str
    model: str
    lint_issues: list[LintIssue]
    detected_version: int | None


class GenerationError(RuntimeError):
    """Raised when Pine Script generation cannot be completed."""


def _extract_code_block(text: str) -> str:
    match = re.search(r"```(?:pine|pinescript)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip() + "\n"
    return text.strip() + "\n"


def generate_pine_script(request: GenerationRequest, api_key: str | None = None) -> GenerationResult:
    """Call the Anthropic API to synthesize Pine Script from a prompt.

    Raises :class:`GenerationError` if no API key is available or the API
    call fails; callers (CLI) should catch this and print a friendly
    message pointing the user at ``ANTHROPIC_API_KEY``.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise GenerationError(
            "No Anthropic API key found. Set the ANTHROPIC_API_KEY environment "
            "variable or pass --api-key to use `pinesprout generate`."
        )

    user_message = (
        f"Script type: {request.script_type}\nTarget Pine version: {request.pine_version}\nRequest: {request.prompt}\n"
    )

    payload = {
        "model": request.model,
        "max_tokens": request.max_tokens,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(ANTHROPIC_API_URL, headers=headers, content=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise GenerationError(f"Anthropic API error ({exc.response.status_code}): {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise GenerationError(f"Failed to reach Anthropic API: {exc}") from exc

    text_parts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
    raw_text = "\n".join(text_parts)
    if not raw_text:
        raise GenerationError("Anthropic API returned no text content.")

    source = _extract_code_block(raw_text)
    issues = Linter.from_source(source).run()

    return GenerationResult(
        prompt=request.prompt,
        source=source,
        model=request.model,
        lint_issues=issues,
        detected_version=detect_version(source),
    )
