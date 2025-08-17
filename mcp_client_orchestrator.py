import asyncio
import argparse
import os
import logging

from orchestrator import answer_master_question
from mcp_client import get_available_server_scripts


async def main() -> None:
    logger = logging.getLogger("mcp_client_orchestrator")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="MCP Orchestrator Client")
    parser.add_argument("--question", "-q", nargs="+", help="Master question to answer", required=True)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model for planning/args")
    args = parser.parse_args()

    qtext = " ".join(args.question)
    logger.info("received master question: %s", qtext)
    logger.info("using LLM model: %s", args.model)
    server_scripts = get_available_server_scripts()
    logger.info("discovered %d server scripts", len(server_scripts))
    for key, path in server_scripts.items():
        logger.debug("server %s -> %s", key, path)
    logger.info("starting orchestrated answer generation")
    result = await answer_master_question(qtext, server_scripts, llm_model=args.model)
    logger.info("orchestration complete; printing result")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())


