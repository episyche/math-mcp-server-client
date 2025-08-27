import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get OpenAI API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file. Please set it in your .env file.")
    
    # Get the current directory for relative path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    telegram_server_path = os.path.join(current_dir, "telegram_mcp_server.py")

    # Create configuration dictionary
    config = {
      "mcpServers": {
        "telegram": {
          "command": "python",
          "args": [telegram_server_path],
        }
      }
    }

    # Create MCPClient from configuration dictionary
    client = MCPClient.from_dict(config)

    # Create LLM with API key from environment
    llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)

    # Create agent with the client
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # Run the query
    result = await agent.run(
        # "Who did I chat with last"
        # "search contact 6384192400 "
        # "list_messages balaji"
        # "get_contact_chats Balaji"
        "show all my contact"
    )

    print("*\n\n")
    print(f"\nResult: {result}")
    print("*\n\n")

if __name__ == "__main__":
    asyncio.run(main())