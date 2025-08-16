from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("ArithmeticServer")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the result."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b and return the quotient. Raises if dividing by zero."""    
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


if __name__ == "__main__":
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()


