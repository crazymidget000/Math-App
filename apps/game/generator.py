"""Database-independent addition and subtraction questions for Stages 1–2."""

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    a: int
    b: int
    operation: str
    answer: int


def _nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _operand_range(params, name, default_max):
    if name not in params:
        if default_max is None:
            raise ValueError(f"{name} is required when no maximum is configured")
        return 0, default_max
    bounds = params[name]
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        raise ValueError(f"{name} must contain two inclusive integer bounds")
    lower, upper = (_nonnegative_integer(value, name) for value in bounds)
    if lower > upper:
        raise ValueError(f"{name} lower bound must not exceed its upper bound")
    return lower, upper


def generate_question(params: dict, rng: Random) -> GeneratedQuestion:
    """Generate a question using the monster's JSON params and the supplied RNG.

    Supports ``add`` (inclusive ``max_sum``) and ``sub`` (inclusive ``max_a``),
    with optional inclusive ``a_range`` and ``b_range``. Omitted ranges default
    to [0, maximum]; zero operands and zero answers are allowed. Explicit ranges
    and maximum constraints apply together. Subtraction always has a >= b.

    Draw a feasible first operand, then a feasible second operand, without
    rejection loops. Invalid or impossible configurations raise ValueError.
    Reuse a seeded Random instance to reproduce an entire question sequence.
    This stateless function leaves battle-level repeat avoidance to the caller.
    """
    operation = params.get("op")
    if operation not in ("add", "sub"):
        raise ValueError("op must be 'add' or 'sub'")

    maximum_key = "max_sum" if operation == "add" else "max_a"
    maximum = (
        _nonnegative_integer(params[maximum_key], maximum_key) if maximum_key in params else None
    )
    a_min, a_max = _operand_range(params, "a_range", maximum)
    b_min, b_max = _operand_range(params, "b_range", maximum)

    if operation == "add":
        if maximum is not None:
            a_max = min(a_max, maximum - b_min)
    else:
        a_min = max(a_min, b_min)
        if maximum is not None:
            a_max = min(a_max, maximum)

    if a_min > a_max:
        raise ValueError("question parameters admit no valid operand pairs")

    a = rng.randint(a_min, a_max)
    if operation == "add":
        if maximum is not None:
            b_max = min(b_max, maximum - a)
        b = rng.randint(b_min, b_max)
        answer, symbol = a + b, "+"
    else:
        b = rng.randint(b_min, min(b_max, a))
        answer, symbol = a - b, "-"
    return GeneratedQuestion(
        prompt=f"{a} {symbol} {b}", a=a, b=b, operation=operation, answer=answer
    )
