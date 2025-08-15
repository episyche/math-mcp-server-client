# math-mcp-server-client

## Servers

- `math_mcp_server.py`: Basic arithmetic tools (add, subtract, multiply, divide)
- `integration_mcp_server.py`: Symbolic and definite integration tools
- `differentiation_mcp_server.py`: Symbolic differentiation tools
- `probability_mcp_server.py`: Common probability operations
- `venn_mcp_server.py`: Venn diagram region calculations (2-set and 3-set)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running a server

Each server is an MCP server over stdio. Launch one with Python:

```bash
python integration_mcp_server.py
```

Replace with any of:

```bash
python differentiation_mcp_server.py
python probability_mcp_server.py
python venn_mcp_server.py
python math_mcp_server.py
```

Your MCP-capable client should connect via stdio and list available tools.

## Tools

### Integration server (`integration_mcp_server.py`)
- `integrate_indefinite(expression: str, variable: str) -> str`
- `integrate_definite(expression: str, variable: str, lower: str, upper: str) -> str`

Examples:

```text
integrate_indefinite("sin(x) + x**2", "x")
integrate_definite("sin(x)", "x", "0", "pi")
```

### Differentiation server (`differentiation_mcp_server.py`)
- `derivative(expression: str, variable: str, order: int = 1) -> str`

Example:

```text
derivative("sin(x) * x**2", "x", 2)
```

### Probability server (`probability_mcp_server.py`)
- `complement(p: float) -> float`
- `union_independent(p_a: float, p_b: float) -> float`
- `intersection_independent(p_a: float, p_b: float) -> float`
- `conditional(p_a_and_b: float, p_b: float) -> float`
- `bayes(p_a: float, p_b_given_a: float, p_b: float) -> float`

### Venn server (`venn_mcp_server.py`)
- `two_set_regions(n_a: int, n_b: int, n_a_intersect_b: int) -> dict`
- `three_set_regions(n_a: int, n_b: int, n_c: int, n_ab: int, n_ac: int, n_bc: int, n_abc: int) -> dict`

