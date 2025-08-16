import asyncio
import os

from mcp_client import handle_question


QUESTIONS = [
    # Arithmetic
    "what is 12 plus 30",
    "divide 10 by 2",
    "what is the difference between 10 and 3",
    # English - grammar
    "please fix grammar in this sentence it be bad",
    # English - translate
    "translate 'Hola, ¿cómo estás?' to English",
    "translate from English to Spanish: 'Good morning, how are you?'",
    # Biology - botany
    "give a brief summary of the plant sunflower",
    "is basil edible",
    "what are medicinal uses of turmeric",
    "compute leaf area index when total leaf area is 12 and ground area is 4",
    "estimate photosynthesis rate with light 800, co2 500 and temperature 25",
    "classify life form for a plant of height 8 meters",
    "what are seed dispersal methods for dandelion",
    "compute drought stress index for soil moisture 12",
    # Biology - zoology
    "give a brief summary of lion",
    "estimate basal metabolic rate for a 70 kg animal",
    "what is the field of view for a predator",
    "estimate max running speed for a 50 kg animal",
    "daily food requirement for a 500 kg herbivore",
    "thermal comfort index at ambient 15 with preferred 20",
    "population growth with r 0.2 starting at 100 for 5 years",
    "predator prey equilibrium with prey growth 0.8, pred efficiency 0.02, pred death 0.1, encounter 0.5",
    "habitat suitability for temperature 22 and rainfall 800",
    "classify diet for teeth shape sharp",
    "lifespan estimate for a 70 kg animal",
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


