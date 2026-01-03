"""Math QA Tool - Answers common math questions from a built-in knowledge base."""
from __future__ import annotations

import re
from pydantic import BaseModel

from ...base import BaseTool


class MathQAArgs(BaseModel):
    question: str


class MathQAOutput(BaseModel):
    question: str
    answer: str


class MathQATool(BaseTool):
    _name = "math_qa"
    _description = "Answers common math Q&A from a built-in knowledge base (no internet required)."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return MathQAArgs

    @property
    def output_schema(self):
        return MathQAOutput

    def execute(self, question: str) -> dict:
        q = question.strip().lower()
        answer = self._lookup(q)
        return MathQAOutput(question=question, answer=answer).model_dump()

    def _lookup(self, q: str) -> str:
        entries: list[tuple[re.Pattern[str], str]] = [
            (re.compile(r"pythagorean theorem"),
             "In a right triangle with legs a and b and hypotenuse c: a^2 + b^2 = c^2."),
            (re.compile(r"quadratic formula"),
             "For ax^2 + bx + c = 0: x = (-b ± sqrt(b^2 - 4ac)) / (2a)."),
            (re.compile(r"area of a circle|circle area"),
             "Area of a circle: A = πr^2. Circumference: C = 2πr."),
            (re.compile(r"circumference of a circle"),
             "Circumference of a circle: C = 2πr (or πd)."),
            (re.compile(r"area of a triangle"),
             "Area of a triangle: A = (1/2)·base·height."),
            (re.compile(r"area of a rectangle"),
             "Area of a rectangle: A = length·width."),
            (re.compile(r"area of a square"),
             "Area of a square: A = side^2. Perimeter: P = 4·side."),
            (re.compile(r"slope[-\s]*intercept form|y\s*=\s*mx\s*\+\s*b"),
             "Slope-intercept form of a line: y = mx + b, where m is slope and b is y-intercept."),
            (re.compile(r"distance formula"),
             "Distance between (x1, y1) and (x2, y2): d = sqrt((x2-x1)^2 + (y2-y1)^2)."),
            (re.compile(r"binomial theorem"),
             "Binomial theorem: (a + b)^n = Σ_{k=0..n} (n choose k) a^{n-k} b^k."),
            (re.compile(r"combinations|n choose k|nCk", re.IGNORECASE),
             "Combinations: C(n,k) = n! / (k!(n-k)!). Permutations: P(n,k) = n! / (n-k)!"),
            (re.compile(r"permutations?"),
             "Permutations: P(n,k) = n! / (n-k)!"),
            (re.compile(r"simple interest"),
             "Simple interest: I = P·r·t, amount A = P(1 + rt)."),
            (re.compile(r"compound interest"),
             "Compound interest: A = P(1 + r/n)^{nt}. Continuous compounding: A = Pe^{rt}."),
            (re.compile(r"mean|average"),
             "Mean: sum of values divided by count. Median: middle value. Mode: most frequent value."),
            (re.compile(r"prime number"),
             "A prime number has exactly two positive divisors: 1 and itself."),
            (re.compile(r"derivative"),
             "The derivative measures instantaneous rate of change; formally f'(x) = lim_{h→0} (f(x+h)-f(x))/h."),
            (re.compile(r"integral"),
             "An integral accumulates area; the indefinite integral is antiderivative F'(x)=f(x), and definite integral ∫_a^b f(x)dx is area under curve."),
        ]
        for pattern, ans in entries:
            if pattern.search(q):
                return ans
        return (
            "I can help with calculations (e.g., 2+2, 20% of 50) "
            "and core math facts like the Pythagorean theorem, quadratic formula, and area/circumference formulas."
        )


