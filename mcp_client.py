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
            # "postgres_server": {
            #     "command": "python",
            #     "args": ["postgres/server.py"],
            # },
            # "google_search_console_server": {
            #     "command": "python",
            #     "args": ["google_search_console/server.py"],
            # },
            # "google_analytics_active_users_server": {
            #     "command": "python",
            #     "args": ["google_analytics/server/active_users_mcp_server.py"],
            # },
            # "google_analytics_audiences_server": {
            #     "command": "python",
            #     "args": ["google_analytics/server/audiences_mcp_server.py"],
            # },
            # "google_analytics_demographics_server": {
            #     "command": "python",
            #     "args": ["google_analytics/server/demographics_mcp_server.py"],
            # },
            "youtube_server": {
                "command": "python",
                "args": ["youtube/youtube_mcp_server_simple.py"],
            },
            # "linkedin_company_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/company_server.py"],
            # },
            # "linkedin_decision_makers_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/decision_makers_server.py"],
            # },
            # "linkedin_enrichment_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/enrich_server.py"],
            # },
            # "linkedin_jobs_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/jobs_server.py"],
            # },
            # "linkedin_posts_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/posts_server.py"],
            # },
            # "linkedin_recommendation_server": {
            #     "command": "python",
            #     "args": ["linkedin/server/recommendation_server.py"],
            # },
            # "instagram_server": {
            #     "command": "python",
            #     "args": ["instagram/server/server.py"],
            # },
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

    # system_rules = f"""
    #     Current Date: {current_date}

    #     You are an assistant with access to tools from MCP.
    #     Different MCP servers provide different tools. Always respect their intended use.

    #     General Rules:
    #     1. Never invent tool names — only use tools discovered from MCP.
    #     2. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
    #     3. Before using any tool, make sure you understand which server it belongs to.

    #     Postgres Database Rules:
    #     1. Only use SELECT queries with execute_sql.
    #     2. If the user asks about tables but not columns, prefer table_list.
    #     3. If the user asks about structure/columns, prefer database_schema.
    #     4. If you need schema of any table, use database_schema.
    #     5. Never modify data (INSERT/UPDATE/DELETE not allowed).

    #     Google Search Console Rules:
    #     1. If the question relates to site performance, queries, clicks, impressions, or position, use the GSC tools.
    #     2. If a site (property) is mentioned, you must provide the property ID in the format required (`sc-domain:example.com` or full URL).
    #     3. For "top queries", "pages", or "countries", use the appropriate discovery tools (e.g., search_analytics).
    #     4. Always return the raw data (clicks, impressions, CTR, position) unless the user requests a summary.
    #     5. If unsure, first list available resources from the GSC server before attempting queries.

    #         ## DIMENSION DETECTION RULES
    #             Auto-detect dimensions from user queries:
    #             - "by query" / "queries" / "search terms" / "keywords" → include "query"
    #             - "by page" / "pages" / "URLs" / "landing pages" → include "page"
    #             - "by country" / "countries" / mention of specific countries → include "country"
    #             - "by device" / "mobile" / "desktop" / "tablet" / "device-wise" → include "device"
    #             - "daily" / "day-wise" / "trends" / "by date" → include "date"
    #             Multi-dimensional queries:
    #             - "by query and device" → dimensions: ["query", "device"]
    #             - "by page and country" → dimensions: ["page", "country"]
    #             - "query performance by device" → dimensions: ["query", "device"]
    #             - "country and device breakdown" → dimensions: ["country", "device"]
    #             - "page + query + country" → dimensions: ["page", "query", "country"]

    #     Google Analytics Rules:
    #     - Before calling any tools related to Google Analytics, use the resource ga4://metrics to get the available metrics.
    #     - Use when the question includes 'daily', 'weekly', or 'monthly' trends.
    #         - Automatically add the correct time dimension:
    #             * 'daily' → add 'date' as dimension
    #             * 'weekly' or 'weeks' → add 'week' as dimension
    #             * 'monthly' or 'months' → add 'month' as dimension
    #             * 'hour' → add 'hour' as dimension
    #             * 'year' → add 'year' as dimension
    #     LinkedIn Rules:
    #     - Before calling any tools related to LinkedIn, use the resource linkedin:/industry_mapping to get the available industries.
    # """

    agent = MCPAgent(llm=llm, client=client, max_steps=2, system_prompt=system_rules)

    # result = await agent.run("retrieve the data from the table cars and print the data", max_steps=10)
    # result = await agent.run("what are the cars brands in the table cars", max_steps=10)
    # result = await agent.run("can you list me all the available resources?", max_steps=10)
    # result = await agent.run("can you list me all the available tables?", max_steps=10)
    # result = await agent.run("give the total no of entries in the table cars", max_steps=10)
    # result = await agent.run("what are the brands available in the db", max_steps=10)
    # result = await agent.run("Which brand has the most models", max_steps=10)

    # YouTube test
    result = await agent.run(
        "get all my videos in youtube for user_id '842a4951-5d0c-40c6-8488-732626d5a3c0'",
        max_steps=10,
    )
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
