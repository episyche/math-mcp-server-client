import asyncio
import argparse
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_server_script_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "math_mcp_server.py")


async def call_tool(session: ClientSession, name: str, **arguments) -> str:
    result = await session.call_tool(name=name, arguments=arguments)

    # Try to extract human-readable text from the result's content items
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

def normalize_operation(op: str | None) -> str | None:
    if op is None:
        return None
    mapping = {
        "add": "add",
        "plus": "add",
        "sum": "add",
        "total": "add",
        "subtract": "subtract",
        "minus": "subtract",
        "difference": "subtract",
        "multiply": "multiply",
        "times": "multiply",
        "product": "multiply",
        "divide": "divide",
        "quotient": "divide",
        "over": "divide",
    }
    return mapping.get(op.lower(), op.lower())

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


def llm_route_question(question: str, model: str | None = None) -> tuple[str | None, float | None, float | None]:
    client = ensure_openai_client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = (
        "You are a precise math tool router. "
        "Extract exactly one operation and two numeric operands from the user's prompt. "
        "Allowed operations: add, subtract, multiply, divide. "
        "Return ONLY a compact JSON object with keys operation (string), a (number), b (number). "
        "If the instruction implies 'subtract X from Y', use a=Y, b=X. "
        "If division by zero is implied, still return the numbers as-is."
    )

    user_prompt = f"User prompt: {question}"

    try:
        # Using Chat Completions with JSON response
        from openai import OpenAI  # type: ignore
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
        print(f"Content: {content}")
        data = json.loads(content)
        op = normalize_operation(data.get("operation"))
        print(f"Operation: {op}")
        a = float(data.get("a")) if data.get("a") is not None else None
        b = float(data.get("b")) if data.get("b") is not None else None
        return op, a, b
    except Exception:
        return None, None, None


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP math client")
    parser.add_argument("--question", "-q", nargs="+", help="Natural language question, e.g. 'what is 3 plus 4'", required=False)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model name for agent mode")
    args = parser.parse_args()

    server_script = get_server_script_path()
    if not os.path.exists(server_script):
        raise FileNotFoundError(f"Server script not found at: {server_script}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if not args.question:
                print("Please provide a question with --question/-q, e.g. --question 'what is 3 plus 4'")
                sys.exit(1)

            qtext = " ".join(args.question)
            operation, a, b = llm_route_question(qtext, model=args.model)

            if operation and a is not None and b is not None:
                result_text = await call_tool(session, operation, a=a, b=b)
                print(result_text)
            else:
                print("LLM could not parse the question. Please rephrase and try again.")


if __name__ == "__main__":
    asyncio.run(main())


