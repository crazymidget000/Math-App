"""Server-only OpenRouter calls. Provider failures never reach the child."""

import json
import math

import httpx
from django.conf import settings

from .validate import validate_hint

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_PROMPT = (
    "You are a kind wizard helping a 6-10 year old with math. Use short, simple sentences. "
    "Explain how to solve the question without stating the final answer. Encourage the child. "
    "Return only a JSON object with encouragement (a nonempty string, at most 160 characters), "
    "steps (1-4 nonempty strings, each at most 160 characters), and strategy "
    "(counting_on, make_ten, count_back, skip_count, arrays, fact_family, or other)."
)


def fallback_hint(operation):
    steps, strategy = {
        "add": (["Start with the first number. Count on by the second number."], "counting_on"),
        "sub": (["Start with the first number. Count back by the second number."], "count_back"),
        "mul": (["Make equal groups. Count how many there are altogether."], "arrays"),
        "div": (["Share the first number into equal groups. Count each group."], "fact_family"),
    }.get(operation, (["Try drawing the numbers to help you think."], "other"))
    return {
        "encouragement": "Good try! Let's work through it.",
        "steps": steps,
        "strategy": strategy,
    }


def request_hint(question):
    """Return (validated hint, status), using only server-owned numeric question data."""
    fallback = fallback_hint(question.operation)
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_MODEL:
        return fallback, "fallback"
    try:
        timeout = float(settings.AI_TIMEOUT_SECONDS)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Invalid timeout")
        response = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "a": question.operand_a,
                                "b": question.operand_b,
                                "operation": question.operation,
                                "child_answer": question.player_answer,
                            }
                        ),
                    },
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 300,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return validate_hint(content), "ok"
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, RecursionError):
        # Do not log provider responses or exception strings: they can contain secrets.
        return fallback, "fallback"
