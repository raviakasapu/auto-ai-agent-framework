"""Calculator Tool - Evaluates arithmetic expressions safely."""
from __future__ import annotations

import ast
import math
import re
from pydantic import BaseModel, Field

from ...base import BaseTool


class CalculatorArgs(BaseModel):
    expression: str = Field(..., description="Mathematical expression or natural language to evaluate")
    precision: int | None = Field(None, description="Optional rounding precision for float results")


class CalculatorOutput(BaseModel):
    expression: str
    normalized_expression: str
    result: float | None
    note: str | None = None


class CalculatorTool(BaseTool):
    _name = "calculator"
    _description = "Evaluates arithmetic expressions safely, including simple natural language forms."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return CalculatorArgs

    @property
    def output_schema(self):
        return CalculatorOutput

    def execute(self, expression: str, precision: int | None = None) -> dict:
        original = expression
        expr = self._normalize_expression(expression)
        self._last_note: str | None = None
        value = self._safe_eval(expr)
        if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isinf(value)):
            if precision is not None:
                value = round(float(value), int(precision))
            result_val: float | None = float(value)
        else:
            result_val = None
        out = CalculatorOutput(
            expression=original,
            normalized_expression=expr,
            result=result_val,
            note=self._last_note,
        )
        self._last_note = None
        return out.model_dump()

    # --- Helpers ---
    def _normalize_expression(self, text: str) -> str:
        t = text.strip().lower()
        t = re.sub(r"\b(what is|what's|calculate|compute|evaluate|solve|please|find)\b[:?,\s]*", "", t)
        t = t.replace("?", " ")
        # Percent-of patterns
        t = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", r"(\1/100)*\2", t)
        t = re.sub(r"(\d+(?:\.\d+)?)\s*percent\s*of\s*(\d+(?:\.\d+)?)", r"(\1/100)*\2", t)
        replacements = [
            (r"to the power of", "**"),
            (r"raised to the power of", "**"),
            (r"raised to", "**"),
            (r"power of", "**"),
            (r"plus", "+"),
            (r"minus", "-"),
            (r"multiplied by", "*"),
            (r"times", "*"),
            (r"x", "*"),
            (r"divided by", "/"),
            (r"over", "/"),
            (r"modulo", "%"),
            (r"mod", "%"),
            (r"remainder", "%"),
            (r"squared", "**2"),
            (r"cubed", "**3"),
        ]
        for pat, sub in replacements:
            t = re.sub(rf"\b{pat}\b", sub, t)
        t = re.sub(r"square\s+root\s+of\s*\(?\s*([\d\.]+)\s*\)?", r"sqrt(\1)", t)
        t = re.sub(r"sqrt\s+of\s*\(?\s*([\d\.]+)\s*\)?", r"sqrt(\1)", t)
        t = t.replace("×", "*").replace("÷", "/")
        t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", t)
        t = t.replace("^", "**")
        t = re.sub(r"\bpi\b", "(pi)", t)
        t = re.sub(r"\be\b", "(e)", t)
        t = t.replace("=", " ")
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _safe_eval(self, expr: str) -> float:
        allowed_funcs = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log10,
            "ln": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "abs": abs,
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
            "pow": pow,
            "factorial": math.factorial,
            "comb": getattr(math, "comb", None),
            "perm": getattr(math, "perm", None),
        }
        allowed_funcs = {k: v for k, v in allowed_funcs.items() if v is not None}
        allowed_names = {"pi": math.pi, "e": math.e, **allowed_funcs}

        node = ast.parse(expr, mode="eval")

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, (int, float)):
                    return n.value
                raise ValueError("Only numeric constants allowed")
            if isinstance(n, ast.BinOp):
                left = _eval(n.left)
                right = _eval(n.right)
                if isinstance(n.op, ast.Add):
                    return left + right
                if isinstance(n.op, ast.Sub):
                    return left - right
                if isinstance(n.op, ast.Mult):
                    return left * right
                if isinstance(n.op, ast.Div):
                    return left / right
                if isinstance(n.op, ast.FloorDiv):
                    return left // right
                if isinstance(n.op, ast.Mod):
                    return left % right
                if isinstance(n.op, ast.Pow):
                    try:
                        a = float(left)
                        b = float(right)
                    except Exception:
                        a, b = left, right
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > 0 and b > 0:
                        try:
                            exp10 = b * math.log10(a)
                            digits = int(math.floor(exp10)) + 1
                            if digits > 10000 or b > 10000:
                                frac, ip = math.modf(exp10)
                                mantissa = 10 ** frac
                                self._last_note = (
                                    f"Result is extremely large (~{digits} digits). Approx ≈ {mantissa:.6f}e{int(ip)}."
                                )
                                return float("inf")
                        except Exception:
                            pass
                    return left ** right
                raise ValueError("Unsupported binary operator")
            if isinstance(n, ast.UnaryOp):
                val = _eval(n.operand)
                if isinstance(n.op, ast.UAdd):
                    return +val
                if isinstance(n.op, ast.USub):
                    return -val
                raise ValueError("Unsupported unary operator")
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name) and n.func.id in allowed_funcs:
                    func = allowed_funcs[n.func.id]
                else:
                    raise ValueError("Call to unsupported function")
                args = [_eval(a) for a in n.args]
                if any(not isinstance(a, (int, float)) for a in args):
                    raise ValueError("Only numeric function arguments allowed")
                return func(*args)
            if isinstance(n, ast.Name):
                if n.id in allowed_names:
                    return allowed_names[n.id]
                raise ValueError(f"Unknown identifier: {n.id}")
            raise ValueError("Unsupported expression element")

        return float(_eval(node))


