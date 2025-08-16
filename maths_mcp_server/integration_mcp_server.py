from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from sympy import Integral, Symbol, sympify
from sympy.core.sympify import SympifyError
from sympy.integrals.integrals import integrate


mcp = FastMCP("IntegrationServer")


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
def integrate_indefinite(expression: str, variable: str) -> str:
    """Compute the indefinite integral ∫ expression d(variable).

    - expression: A string representing a SymPy-compatible expression, e.g. "sin(x) + x**2".
    - variable: The variable of integration, e.g. "x".
    Returns a stringified symbolic result.
    """
    var = _parse_symbol(variable)
    expr = _parse_expression(expression)
    result = integrate(expr, var)
    return str(result)


@mcp.tool()
def integrate_definite(expression: str, variable: str, lower: str, upper: str) -> str:
    """Compute the definite integral ∫[lower, upper] expression d(variable).

    - expression: SymPy-compatible expression string.
    - variable: Variable of integration, e.g. "x".
    - lower: Lower bound (string allowed, will be sympified), e.g. "0" or "pi/2".
    - upper: Upper bound (string allowed, will be sympified), e.g. "1" or "pi".
    Returns a string with exact value and numeric approximation if available.
    """
    var = _parse_symbol(variable)
    expr = _parse_expression(expression)
    a = _parse_expression(lower)
    b = _parse_expression(upper)
    integral_obj = Integral(expr, (var, a, b))
    exact_value = integral_obj.doit()
    try:
        numeric_value = exact_value.evalf()
        return f"exact={exact_value}; numeric≈{numeric_value}"
    except Exception:
        return f"exact={exact_value}"


if __name__ == "__main__":
    mcp.run()


