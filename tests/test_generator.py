"""Stage 1–2 fixtures mirror docs/plan.md, section 6; no database needed."""

import random
import unittest
from copy import deepcopy

from apps.game.generator import generate_question

PARAMETER_SETS = {
    "stage1_slime": {"op": "add", "max_sum": 10},
    "stage1_goblin": {"op": "add", "max_sum": 20},
    "stage1_troll": {"op": "add", "a_range": [10, 99], "b_range": [1, 9]},
    "stage1_boss": {"op": "add", "a_range": [10, 99], "b_range": [10, 99], "max_sum": 100},
    "stage2_monster1": {"op": "sub", "max_a": 10},
    "stage2_monster2": {"op": "sub", "max_a": 20},
    "stage2_monster3": {"op": "sub", "a_range": [20, 99], "b_range": [1, 9]},
    "stage2_boss": {"op": "sub", "a_range": [20, 100], "b_range": [10, 99]},
}


class GeneratorTests(unittest.TestCase):
    def test_every_monster_constraints_and_arithmetic(self):
        for name, params in PARAMETER_SETS.items():
            with self.subTest(monster=name):
                original = deepcopy(params)
                rng = random.Random(42)
                questions = [generate_question(params, rng) for _ in range(1000)]
                self.assertGreater(len(set(questions)), 1)
                for q in questions:
                    self.assertEqual(q.operation, params["op"])
                    for value in (q.a, q.b, q.answer):
                        self.assertIs(type(value), int)
                        self.assertGreaterEqual(value, 0)
                    for key, value in (("a_range", q.a), ("b_range", q.b)):
                        if key in params:
                            self.assertLessEqual(params[key][0], value)
                            self.assertLessEqual(value, params[key][1])
                    if q.operation == "add":
                        self.assertEqual(q.answer, q.a + q.b)
                        self.assertEqual(q.prompt, f"{q.a} + {q.b}")
                        if "max_sum" in params:
                            self.assertLessEqual(q.answer, params["max_sum"])
                    else:
                        self.assertEqual(q.answer, q.a - q.b)
                        self.assertEqual(q.prompt, f"{q.a} - {q.b}")
                        self.assertGreaterEqual(q.a, q.b)
                        if "max_a" in params:
                            self.assertLessEqual(q.a, params["max_a"])
                self.assertEqual(params, original)

    def test_seed_reproduces_each_monster_sequence(self):
        for name, params in PARAMETER_SETS.items():
            with self.subTest(monster=name):
                first, second = random.Random(123), random.Random(123)
                global_state = random.getstate()
                self.assertEqual(
                    [generate_question(params, first) for _ in range(50)],
                    [generate_question(params, second) for _ in range(50)],
                )
                self.assertEqual(random.getstate(), global_state)

    def test_inclusive_bounds_zero_and_single_possible_pair(self):
        cases = [
            ({"op": "add", "max_sum": 0}, (0, 0, 0)),
            ({"op": "sub", "max_a": 0}, (0, 0, 0)),
            (
                {"op": "add", "a_range": [90, 99], "b_range": [10, 99], "max_sum": 100},
                (90, 10, 100),
            ),
            ({"op": "sub", "a_range": [20, 30], "b_range": [30, 99]}, (30, 30, 0)),
            ({"op": "add", "a_range": [99, 99], "b_range": [9, 9]}, (99, 9, 108)),
            ({"op": "sub", "a_range": [100, 100], "b_range": [10, 10]}, (100, 10, 90)),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                q = generate_question(params, random.Random(42))
                self.assertEqual((q.a, q.b, q.answer), expected)

    def test_invalid_or_impossible_parameters(self):
        cases = [
            {},
            {"op": "mul"},
            {"op": "add"},
            {"op": "sub"},
            {"op": "add", "max_sum": -1},
            {"op": "sub", "max_a": True},
            {"op": "add", "max_sum": 1.5},
            {"op": "add", "a_range": [9, 2], "b_range": [1, 9]},
            {"op": "add", "a_range": [-1, 2], "b_range": [1, 9]},
            {"op": "add", "a_range": [1], "b_range": [1, 9]},
            {"op": "add", "a_range": None, "max_sum": 10},
            {"op": "add", "a_range": [True, 2], "max_sum": 10},
            {"op": "add", "a_range": [10, 20], "b_range": [10, 20], "max_sum": 19},
            {"op": "sub", "a_range": [1, 2], "b_range": [3, 4]},
            {"op": "sub", "a_range": [20, 30], "b_range": [1, 9], "max_a": 10},
        ]
        for params in cases:
            with self.subTest(params=params), self.assertRaises(ValueError):
                generate_question(params, random.Random(42))
