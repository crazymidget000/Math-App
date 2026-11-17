"""Validate the small, structured hint used by the battle page."""

import json

STRATEGIES = frozenset(
    {"counting_on", "make_ten", "count_back", "skip_count", "arrays", "fact_family", "other"}
)


def _valid_text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 160 or "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def validate_hint(content):
    """Return only validated display fields, or raise ValueError."""
    if not isinstance(content, str):
        raise ValueError("Hint must be JSON text")
    try:
        data = json.loads(content)
    except RecursionError as error:
        raise ValueError("Hint JSON is too deeply nested") from error
    if not isinstance(data, dict):
        raise ValueError("Hint must be an object")
    encouragement = data.get("encouragement")
    steps = data.get("steps")
    strategy = data.get("strategy")
    if (
        not _valid_text(encouragement)
        or not isinstance(steps, list)
        or not 1 <= len(steps) <= 4
        or any(not _valid_text(step) for step in steps)
        or not isinstance(strategy, str)
        or strategy not in STRATEGIES
    ):
        raise ValueError("Invalid hint fields")
    return {"encouragement": encouragement, "steps": steps, "strategy": strategy}
