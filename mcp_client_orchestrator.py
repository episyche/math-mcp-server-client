import asyncio
import argparse
import os
import logging

from orchestrator import answer_master_question, ensure_openai_client
from mcp_client import get_available_server_scripts


async def main() -> None:
    logger = logging.getLogger("mcp_client_orchestrator")
    if not logger.handlers:
        logging.basicConfig(level=logging.WARNING)
    
    def humanize_with_openai(text: str, model: str) -> str:
        """Convert raw/JSON tool result into human-readable text via OpenAI."""
        try:
            client = ensure_openai_client()
            system_prompt = (
                "You convert raw tool outputs (often JSON arrays/objects) into concise, readable summaries. "
                "When the input looks like a list of YouTube videos, render a numbered list with: Title — date — https://youtu.be/<id>. "
                "When it is analytics or a single object, produce a short labeled summary. "
                "If it's already plain text, keep it concise. Output plain text only (no code fences)."
            )
            user_prompt = f"Tool Result to humanize:\n\n{text}"
            resp = client.chat.completions.create(
                model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            content = resp.choices[0].message.content or ""
            return content.strip()
        except Exception:
            # Fallback: return original text if LLM call fails
            return text
    parser = argparse.ArgumentParser(description="MCP Orchestrator Client")
    parser.add_argument("--question", "-q", nargs="+", help="Master question to answer", required=True)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model for planning/args")
    args = parser.parse_args()

    qtext = " ".join(args.question)
    logger.debug("received master question: %s", qtext)
    logger.debug("using LLM model: %s", args.model)
    server_scripts = get_available_server_scripts()
    logger.debug("discovered %d server scripts", len(server_scripts))
    for key, path in server_scripts.items():
        logger.debug("server %s -> %s", key, path)
    logger.debug("starting orchestrated answer generation")
    result = await answer_master_question(qtext, server_scripts, llm_model=args.model)
    logger.debug("orchestration complete; printing result", result)
    # print(result)
    print(humanize_with_openai(result, args.model))


if __name__ == "__main__":
    asyncio.run(main())



