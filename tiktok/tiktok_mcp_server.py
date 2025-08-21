from __future__ import annotations

import os
from typing import Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TikTokServer")

# Load env from both local .env (inside tiktok/) and project root .env
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

API_BASE = "https://tikneuron.com/api/mcp"


def _api_key() -> str:
    key = os.getenv("TIKNEURON_MCP_API_KEY", "").strip()
    if not key:
        raise RuntimeError("TIKNEURON_MCP_API_KEY not set")
    return key


def _headers() -> dict:
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "MCP-API-KEY": _api_key(),
    }


@mcp.tool()
def tiktok_search(query: str, cursor: Optional[str] = None, search_uid: Optional[str] = None) -> str:
    url = f"{API_BASE}/search"
    params: dict = {"query": query}
    if cursor:
        params["cursor"] = cursor
    if search_uid:
        params["search_uid"] = search_uid

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    data = resp.json()

    videos = data.get("videos") or []
    if not videos:
        return "No videos found for the search query"

    lines = []
    for idx, v in enumerate(videos, start=1):
        lines.append(
            "\n".join(
                [
                    f"Video {idx}:",
                    f"Description: {v.get('description') or 'N/A'}",
                    f"Video ID: {v.get('video_id') or 'N/A'}",
                    f"Creator: {v.get('creator') or 'N/A'}",
                    f"Hashtags: {', '.join(v.get('hashtags') or []) or 'N/A'}",
                    f"Likes: {v.get('likes') or '0'}",
                    f"Shares: {v.get('shares') or '0'}",
                    f"Comments: {v.get('comments') or '0'}",
                    f"Views: {v.get('views') or '0'}",
                    f"Bookmarks: {v.get('bookmarks') or '0'}",
                    f"Created at: {v.get('created_at') or 'N/A'}",
                    f"Duration: {v.get('duration') or 0} seconds",
                    "Available subtitles: "
                    + (
                        ", ".join(
                            f"{s.get('language') or 'Unknown'} ({s.get('source') or 'Unknown source'})"
                            for s in (v.get('available_subtitles') or [])
                        )
                        or "None"
                    ),
                ]
            )
        )

    meta = data.get("metadata") or {}
    lines.append(
        "\n".join(
            [
                "",
                "Search Metadata:",
                f"Cursor: {meta.get('cursor') or 'N/A'}",
                f"Has more results: {'Yes' if meta.get('has_more') else 'No'}",
                f"Search UID: {meta.get('search_uid') or 'N/A'}",
            ]
        )
    )

    return "\n\n".join(lines)


@mcp.tool()
def tiktok_get_subtitle(tiktok_url: str, language_code: Optional[str] = None) -> str:
    url = f"{API_BASE}/get-subtitles"
    params: dict = {"tiktok_url": tiktok_url}
    if language_code:
        params["language_code"] = language_code

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("subtitle_content") or "No subtitle available"


@mcp.tool()
def tiktok_get_post_details(tiktok_url: str) -> str:
    url = f"{API_BASE}/post-detail"
    params = {"tiktok_url": tiktok_url}

    resp = requests.get(url, headers=_headers(), params=params)
    resp.raise_for_status()
    d = (resp.json() or {}).get("details") or {}
    return "\n".join(
        [
            f"Description: {d.get('description') or 'N/A'}",
            f"Video ID: {d.get('video_id') or 'N/A'}",
            f"Creator: {d.get('creator') or 'N/A'}",
            f"Hashtags: {', '.join(d.get('hashtags') or []) or 'N/A'}",
            f"Likes: {d.get('likes') or '0'}",
            f"Shares: {d.get('shares') or '0'}",
            f"Comments: {d.get('comments') or '0'}",
            f"Views: {d.get('views') or '0'}",
            f"Bookmarks: {d.get('bookmarks') or '0'}",
            f"Created at: {d.get('created_at') or 'N/A'}",
            f"Duration: {d.get('duration') or 0} seconds",
            "Available subtitles: "
            + (
                ", ".join(
                    f"{s.get('language') or 'Unknown'} ({s.get('source') or 'Unknown source'})"
                    for s in (d.get('available_subtitles') or [])
                )
                or "None"
            ),
        ]
    )


if __name__ == "__main__":
    mcp.run()


