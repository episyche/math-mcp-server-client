# math-mcp-server-client

## Servers

All math-related MCP servers are grouped under the `maths_mcp_server/` package:

- `maths_mcp_server/arithmetic_mcp_server.py`: Basic arithmetic tools (add, subtract, multiply, divide)
- `maths_mcp_server/integration_mcp_server.py`: Symbolic and definite integration tools
- `maths_mcp_server/differentiation_mcp_server.py`: Symbolic differentiation tools
- `maths_mcp_server/probability_mcp_server.py`: Common probability operations
- `maths_mcp_server/venn_mcp_server.py`: Venn diagram region calculations (2-set and 3-set)

All English-related MCP servers are grouped under the `english_mcp_server/` package:

- `english_mcp_server/grammar_mcp_server.py`: Grammar checking for English text
- `english_mcp_server/translate_mcp_server.py`: Translate to English and from English to a target language

All Biology-related MCP servers are grouped under the `biology_mcp_server/` package:

- `biology_mcp_server/botany_mcp_server.py`: Plant utilities (summaries, taxonomy, growth, indices)
- `biology_mcp_server/zoology_mcp_server.py`: Animal utilities (summaries, metabolism, ecology)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running a server

Each server is an MCP server over stdio. Launch one with Python:

```bash
python maths_mcp_server/integration_mcp_server.py
```

Replace with any of:

```bash
python maths_mcp_server/differentiation_mcp_server.py
python maths_mcp_server/probability_mcp_server.py
python maths_mcp_server/venn_mcp_server.py
python maths_mcp_server/arithmetic_mcp_server.py
python english_mcp_server/grammar_mcp_server.py
python english_mcp_server/translate_mcp_server.py
python biology_mcp_server/botany_mcp_server.py
python biology_mcp_server/zoology_mcp_server.py
```

Your MCP-capable client should connect via stdio and list available tools.

## Tools

### English servers
- Grammar (`english_mcp_server/grammar_mcp_server.py`)
  - `check_grammar(text: str, use_languagetool: bool = True) -> dict`
- Translate (`english_mcp_server/translate_mcp_server.py`)
  - `translate_to_english(text: str, source_language: str | None = None) -> str`
  - `translate_from_english(text: str, target_language: str) -> str`

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

