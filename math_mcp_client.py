import asyncio
import argparse
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_available_server_scripts() -> dict[str, str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        "math": os.path.join(current_dir, "math_mcp_server.py"),
        "integration": os.path.join(current_dir, "integration_mcp_server.py"),
        "differentiation": os.path.join(current_dir, "differentiation_mcp_server.py"),
        "probability": os.path.join(current_dir, "probability_mcp_server.py"),
        "venn": os.path.join(current_dir, "venn_mcp_server.py"),
    }


async def call_tool(session: ClientSession, name: str, **arguments) -> str:
    result = await session.call_tool(name=name, arguments=arguments)
    try:
        content_items = getattr(result, "content", []) or []
        if content_items:
            first = content_items[0]
            text = getattr(first, "text", None)
            if text is not None:
                return text
        return str(result)
    except Exception:
        return str(result)


def ensure_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export OPENAI_API_KEY.")
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "OpenAI SDK not installed. Install 'openai' or run 'pip install -r requirements.txt'."
        ) from exc
    return OpenAI()


def llm_route_task(question: str, model: str | None = None) -> tuple[str | None, str | None, dict | None]:
    client = ensure_openai_client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = (
        "You route math queries to MCP servers and tools. "
        "Choose exactly one server and one tool and return arguments. "
        "Servers and tools:\n"
        "- math: add(a,b), subtract(a,b), multiply(a,b), divide(a,b)\n"
        "- integration: integrate_indefinite(expression, variable), integrate_definite(expression, variable, lower, upper)\n"
        "- differentiation: derivative(expression, variable, order)\n"
        "- probability: complement(p), union_independent(p_a, p_b), intersection_independent(p_a, p_b), conditional(p_a_and_b, p_b), bayes(p_a, p_b_given_a, p_b)\n"
        "- venn: two_set_regions(n_a, n_b, n_a_intersect_b), three_set_regions(n_a, n_b, n_c, n_ab, n_ac, n_bc, n_abc)\n"
        "Rules: Return ONLY JSON with keys server, tool, arguments. "
        "Use numbers for numeric fields. Use strings for expressions/variables/bounds. "
        "Prefer Pythonic exponent '**' in expressions. If the query mentions 'from A to B', use definite integral with lower=A, upper=B."
    )

    user_prompt = f"Question: {question}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        server = str(data.get("server")) if data.get("server") is not None else None
        tool = str(data.get("tool")) if data.get("tool") is not None else None
        arguments = data.get("arguments") if isinstance(data.get("arguments"), dict) else None
        return server, tool, arguments
    except Exception:
        return None, None, None


def _normalize_arguments(server: str, tool: str, args: dict) -> dict:
    # Cast types as expected by servers
    if server == "math":
        return {"a": float(args.get("a")), "b": float(args.get("b"))}
    if server == "integration":
        if tool == "integrate_indefinite":
            return {"expression": str(args.get("expression")), "variable": str(args.get("variable"))}
        if tool == "integrate_definite":
            return {
                "expression": str(args.get("expression")),
                "variable": str(args.get("variable")),
                "lower": str(args.get("lower")),
                "upper": str(args.get("upper")),
            }
    if server == "differentiation":
        order_val = args.get("order", 1)
        try:
            order_int = int(order_val)
        except Exception:
            order_int = 1
        return {
            "expression": str(args.get("expression")),
            "variable": str(args.get("variable")),
            "order": order_int,
        }
    if server == "probability":
        # Convert any present numeric args to float
        normalized = {}
        for key, value in args.items():
            try:
                normalized[key] = float(value)
            except Exception:
                normalized[key] = value
        return normalized
    if server == "venn":
        # Convert any present numeric args to int
        normalized = {}
        for key, value in args.items():
            try:
                normalized[key] = int(value)
            except Exception:
                normalized[key] = value
        return normalized
    return args


async def handle_question(question: str, model: str | None = None) -> str:
    server, tool, arguments = llm_route_task(question, model=model)
    if not server or not tool or not arguments:
        return "Router could not determine server/tool/arguments. Please rephrase your question."

    server_scripts = get_available_server_scripts()
    server_script = server_scripts.get(server)
    if not server_script or not os.path.exists(server_script):
        return f"Selected server '{server}' is not available."

    normalized_args = _normalize_arguments(server, tool, arguments)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result_text = await call_tool(session, tool, **normalized_args)
            return result_text


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP multi-math client")
    parser.add_argument("--question", "-q", nargs="+", help="Natural language question", required=True)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model name for routing")
    args = parser.parse_args()

    qtext = " ".join(args.question)
    result = await handle_question(qtext, model=args.model)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())


