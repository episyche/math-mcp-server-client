"""
pip install mcp-use
pip install langchain-openai
"""

import asyncio
import os
from datetime import datetime

from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient


async def main():
    current_date = datetime.now().strftime("%Y-%m-%d")

    config = {
        "mcpServers": {            
            "youtube_server": {
                "command": "python",
                "args": ["youtube/youtube_mcp_server.py"],
            }
        }
    }

    client = MCPClient.from_dict(config)
    print(client, '==========', config)
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))  # or any LLM supported by LangChain

    system_rules = f"""
    You are a YouTube assistant with access to the 'YouTube MCP Server'.
    This server exposes tools to perform CRUD operations on the YouTube Data API v3

    Current Date: {current_date}

    Rules:
    1. Only use tools provided by MCP discovery.
    2. Never invent tool names — only use tools provided by MCP discovery.
    3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
    4. For video operations, always require a user_id parameter.
    5. When searching videos, provide a clear query string.
    6. For analytics, specify the exact video_id when requesting video-specific analytics.
    7. Channel analytics are available for the authenticated user's channel.
    8. Handle authentication errors gracefully - inform users if re-authentication is needed.
    9. For video listings, return comprehensive data including view counts, like counts, and thumbnails.
    10. When users ask about "my videos" or "my channel", use the appropriate tools with their user_id.
    11. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    12. If no user_id is provided in the query, ask the user to provide one.
    """
   
    #test the mcp server
    #result = await client.call_tool("youtube_server", "get_all_videos", "842a4951-5d0c-40c6-8488-732626d5a3c0")
    #print("Result:", result)

    agent = MCPAgent(llm=llm, client=client, max_steps=2, system_prompt=system_rules)
    
    # YouTube test
    result = await agent.run(
        "get all my videos in youtube for user_id '842a4951-5d0c-40c6-8488-732626d5a3c0'",
        max_steps=10,
    )
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
