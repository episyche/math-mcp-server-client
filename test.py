import asyncio
import os

from math_mcp_client import handle_question


QUESTIONS = [
    # Arithmetic
    "what is 12 plus 30",
    "divide 10 by 2",
    "what is the difference between 10 and 3",
    # Differentiation
    "differentiate sin(x) * x**2 with respect to x",
    "find the second derivative of x**5 with respect to x",
    # Integration
    "integrate sin(x) from 0 to pi",
    "find the indefinite integral of x**3 with respect to x",
    # Probability
    "if P(A)=0.3 and P(B)=0.5 and they are independent, what is P(A union B)",
    "what is the conditional probability P(A|B) if P(A and B)=0.12 and P(B)=0.4",
    # Venn
    "In a class, |A|=30, |B|=40, and |A and B|=10. Find only A, only B, both, and union",
    "Three sets: |A|=40, |B|=50, |C|=60, |A∩B|=20, |A∩C|=25, |B∩C|=15, |A∩B∩C|=5. Compute regions",
]


async def run_all(model: str | None = None) -> None:
    for q in QUESTIONS:
        try:
            print(f"\nQ: {q}")
            result = await handle_question(q, model=model)
            print(f"A: {result}")
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    # Ensure API key presence for routing
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Routing will fail.")
    asyncio.run(run_all(os.getenv("OPENAI_MODEL", "gpt-4o-mini")))


