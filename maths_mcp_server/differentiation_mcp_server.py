from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from sympy import Symbol, diff, sympify
from sympy.core.sympify import SympifyError


mcp = FastMCP("DifferentiationServer")


def _parse_symbol(symbol_name: str) -> Symbol:
    if not symbol_name or not symbol_name.strip():
        raise ValueError("Variable name must be a non-empty string.")
    return Symbol(symbol_name)


def _parse_expression(expression: str):
    try:
        return sympify(expression)
    except SympifyError as exc:
        raise ValueError(f"Invalid expression: {expression}") from exc


@mcp.tool()
def derivative(expression: str, variable: str, order: int = 1) -> str:
    """Compute the n-th derivative d^n/d(variable)^n of an expression.

    - expression: SymPy-compatible expression string, e.g. "sin(x) * x**2".
    - variable: Variable for differentiation, e.g. "x".
    - order: Positive integer derivative order (default 1).
    Returns a stringified symbolic result.
    """
    if order < 1:
        raise ValueError("order must be >= 1")
    var = _parse_symbol(variable)
    expr = _parse_expression(expression)
    result = diff(expr, var, order)
    return str(result)


if __name__ == "__main__":
    mcp.run()


