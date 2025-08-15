from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("ProbabilityServer")


def _validate_prob(p: float) -> float:
    if p < 0 or p > 1:
        raise ValueError("Probability must be between 0 and 1 inclusive.")
    return p


@mcp.tool()
def complement(p: float) -> float:
    """Return P(not A) given P(A)=p."""
    return 1.0 - _validate_prob(p)


@mcp.tool()
def union_independent(p_a: float, p_b: float) -> float:
    """For independent A, B: P(A ∪ B) = p_a + p_b - p_a*p_b."""
    p_a = _validate_prob(p_a)
    p_b = _validate_prob(p_b)
    return p_a + p_b - p_a * p_b


@mcp.tool()
def intersection_independent(p_a: float, p_b: float) -> float:
    """For independent A, B: P(A ∩ B) = p_a * p_b."""
    p_a = _validate_prob(p_a)
    p_b = _validate_prob(p_b)
    return p_a * p_b


@mcp.tool()
def conditional(p_a_and_b: float, p_b: float) -> float:
    """P(A|B) = P(A ∩ B) / P(B)."""
    p_a_and_b = _validate_prob(p_a_and_b)
    p_b = _validate_prob(p_b)
    if p_b == 0:
        raise ValueError("P(B) cannot be zero for conditional probability.")
    return p_a_and_b / p_b


@mcp.tool()
def bayes(p_a: float, p_b_given_a: float, p_b: float) -> float:
    """Bayes' theorem: P(A|B) = P(B|A) * P(A) / P(B)."""
    p_a = _validate_prob(p_a)
    p_b_given_a = _validate_prob(p_b_given_a)
    p_b = _validate_prob(p_b)
    if p_b == 0:
        raise ValueError("P(B) cannot be zero for Bayes' theorem.")
    return p_b_given_a * p_a / p_b


if __name__ == "__main__":
    mcp.run()


