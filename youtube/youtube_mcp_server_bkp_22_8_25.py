from __future__ import annotations

import io
import logging
import os
import sys

import requests
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("YoutubeServer")
import json

from mcp.types import CallToolResult, TextContent

# Path to .env file
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# Load environment variables at startup
load_dotenv(ENV_PATH)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Configure logging
logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("YoutubeServer")

def update_env(key: str, value: str):
    """Update or add a key=value pair in .env and reload."""
    set_key(ENV_PATH, key, value)
    os.environ[key] = value  # also refresh current process


def get_access_token():
    return os.getenv("YOUTUBE_ACCESS_TOKEN")


# ---------------------------
# Refresh Token
# ---------------------------
@mcp.tool()
def refresh_token():
    print("**************** REFRESH TOKEN CALLED **********************")
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
        "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        new_token = response.json().get("access_token")
        update_env("YOUTUBE_ACCESS_TOKEN", new_token)
        logger.info("✅ Refreshed token and updated .env")
        return new_token
    else:
        print("❌ Failed to refresh token:", response.json())
        return None


# ---------------------------
# Retry Wrapper for API calls
# ---------------------------
def call_youtube_api(api_func):
    """
    Wrapper: calls YouTube API with current token,
    refreshes once if 401 Unauthorized.
    """
    token = get_access_token()
    try:
        return api_func(token)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("⚠️ Token expired. Refreshing...")
            new_token = refresh_token()
            if new_token:
                return api_func(new_token)
        raise


# ---------------------------
# Tools
# ---------------------------
@mcp.tool()
def list_videos():
    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCLGD-8ZCVuoOcloEdW1lGHg")

    def fetch_videos(token):
        headers = {"Authorization": f"Bearer {token}"}
        search_url = "https://www.googleapis.com/youtube/v3/channels"
        search_params = {"part": "contentDetails", "id": CHANNEL_ID}
        response = requests.get(search_url, headers=headers, params=search_params)
        response.raise_for_status()
        uploads_playlist_id = response.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        playlist_params = {
            "part": "snippet,contentDetails",
            "maxResults": 50,
            "playlistId": uploads_playlist_id,
        }
        response = requests.get(playlist_url, headers=headers, params=playlist_params)
        response.raise_for_status()

        videos = []
        for item in response.json().get("items", []):
            content_details = item.get("contentDetails", {}) or {}
            snippet = item.get("snippet", {}) or {}
            videos.append(
                {
                    "video_id": content_details.get("videoId")
                    or (snippet.get("resourceId", {}) or {}).get("videoId", ""),
                    "title": snippet.get("title", ""),
                    # Fall back to snippet.publishedAt if contentDetails.videoPublishedAt is missing
                    "published_at": content_details.get("videoPublishedAt")
                    or snippet.get("publishedAt", ""),
                }
            )
        return videos  

    videos = call_youtube_api(fetch_videos)
    return CallToolResult(
    content=[
        TextContent(
            type="text",
            text=json.dumps(videos, indent=2, ensure_ascii=False)
        )
    ]
)

@mcp.tool()
def search_videos(arguments: dict):
    """
    Search videos in your channel.
    arguments dict must contain:
        - query: search text
    """

    query = arguments.get("query", "my first")
    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCLGD-8ZCVuoOcloEdW1lGHg")

    def fetch_videos(token):
        headers = {"Authorization": f"Bearer {token}"}
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "channelId": CHANNEL_ID,
            "type": "video",
            "maxResults": 50,
            "q": query,
            "order": "relevance"
        }
        response = requests.get(search_url, headers=headers, params=search_params)
        response.raise_for_status()

        videos = []
        for item in response.json().get("items", []):
            videos.append(
                {
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "channelTitle": item["snippet"]["channelTitle"],
                    "channelId": item["snippet"]["channelId"],
                }
            )
        return videos

    videos = call_youtube_api(fetch_videos)
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(videos, indent=2, ensure_ascii=False)
            )
        ]
    )


@mcp.tool()
def upload_video(arguments: dict):
    """
    Upload a video to YouTube.
    arguments dict must contain:
        - file: path to video
        - title: video title
        - description (optional)
        - tags (optional)
        - categoryId (optional)
        - privacyStatus (optional)
    """
    logger.info("Upload video called with arguments: %s", arguments)
    file = arguments.get("file")
    title = arguments.get("title")
    description = arguments.get("description", "")
    tags = arguments.get("tags", ["api", "youtube", "upload"])
    categoryId = arguments.get("categoryId", "22")
    privacyStatus = arguments.get("privacyStatus", "public")

    if not file or not title:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ 'file' and 'title' are required.")]
        )

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    def upload_video_api(token):
        url = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=multipart"

        metadata = {
            "snippet": {"title": title, "description": description, "tags": tags, "categoryId": categoryId},
            "status": {"privacyStatus": privacyStatus}
        }

        files = {
            "metadata": ("metadata.json", json.dumps(metadata), "application/json; charset=UTF-8"),
            "video": ("video.mp4", open(file, "rb"), "video/mp4")
        }

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(url, headers=headers, files=files)
        print('upload_video_api response: ', response, type(response), response.text)
        response.raise_for_status()
        return response.json()

    try:
        result = call_youtube_api(upload_video_api)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Upload failed: {e.response.text}")]
        )

@mcp.tool()
def add_comment(arguments: dict):
    """
    Post a top-level comment to a YouTube video.
    arguments dict must contain:
        - video_id: ID of the video
        - text: comment text
    """

    video_id = arguments.get("video_id")
    text = arguments.get("text")

    if not video_id or not text:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ 'video_id' and 'text' are required.")]
        )

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    def post_comment_api(token):
        url = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {"textOriginal": text}
                }
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    try:
        result = call_youtube_api(post_comment_api)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Comment failed: {e.response.text}")]
        )

@mcp.tool()
def reply_comment(arguments: dict):

    comment_id = arguments.get("comment_id")
    text = arguments.get("text")

    if not comment_id or not text:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ comment_id or text missing")]
        )

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    def post_reply_api(token):
        url = "https://www.googleapis.com/youtube/v3/comments?part=snippet"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "snippet": {
                "parentId": comment_id,
                "textOriginal": text
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    try:
        result = call_youtube_api(post_reply_api)
        return CallToolResult(
            content=[TextContent(type="text", text=f"✅ Reply posted!\n\n{json.dumps(result, indent=2, ensure_ascii=False)}")]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Reply failed: {e.response.text}")])

@mcp.tool()
def get_video_comments(arguments: dict):
    """
    Fetch top-level comments for a YouTube video.
    Arguments:
        - video_id: ID of the YouTube video
        - max_results: (optional) number of comments to fetch, default 100
    """

    video_id = arguments.get("video_id")
    max_results = arguments.get("max_results", 100)

    if not video_id:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ Missing 'video_id' argument")]
        )

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    def fetch_comments(token):
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": max_results
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        return data

    try:
        comments = call_youtube_api(fetch_comments)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(comments, indent=2, ensure_ascii=False))]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Failed to fetch comments: {e.response.text}")]
        )

@mcp.tool()
def rate_video(arguments: dict):
    """
    Rate a YouTube video via API.
    Args:
        arguments: {"video_id": "<id>", "rating": "like|dislike|none"}
    """

    video_id = arguments.get("video_id")
    rating = arguments.get("rating", "like")

    def rate_video_api(token):
        url = f"https://www.googleapis.com/youtube/v3/videos/rate?id={video_id}&rating={rating}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(url, headers=headers)
        if response.status_code == 204:
            return {"message": f"✅ Video {video_id} rated '{rating}' successfully!"}
        else:
            return {"error": f"❌ Failed with status {response.status_code}: {response.text}"}

    try:
        result = call_youtube_api(rate_video_api)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Rating failed: {str(e)}")]
        )

@mcp.tool()
def video_analytics(arguments: dict):
    """
    Fetch YouTube video analytics for a given video ID.
    Returns statistics like view count, like count, comment count, etc.
    """
    video_id = arguments.get("video_id")
    if not video_id:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ Missing 'video_id' argument")]
        )

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    def fetch_stats(token):
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("items"):
            return {"error": "Video not found"}
        
        item = data["items"][0]
        return {
            "video_id": video_id,
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
            "channel_title": item["snippet"]["channelTitle"],
            "statistics": item.get("statistics", {}),
            "duration": item.get("contentDetails", {}).get("duration", "")
        }

    try:
        stats = call_youtube_api(fetch_stats)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(stats, indent=2, ensure_ascii=False))]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Failed to fetch analytics: {e.response.text}")]
        )


@mcp.tool()
def channel_analytics(channel_id: str = None):
    """
    Get analytics for a YouTube channel: subscribers, total views, total videos.
    """

    token = get_access_token()
    if not token:
        return CallToolResult(
            content=[TextContent(type="text", text="❌ No YOUTUBE_ACCESS_TOKEN in .env")]
        )

    channel_id = channel_id or os.getenv("YOUTUBE_CHANNEL_ID")

    def fetch_channel_stats(token):
        url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "items" not in data or not data["items"]:
            return {"error": "Channel not found"}
        stats = data["items"][0]["statistics"]
        return {
            "channel_id": channel_id,
            "subscribers": stats.get("subscriberCount", "0"),
            "total_views": stats.get("viewCount", "0"),
            "total_videos": stats.get("videoCount", "0"),
        }

    stats = call_youtube_api(fetch_channel_stats)
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(stats, indent=2, ensure_ascii=False))])

@mcp.tool()
def remove_video(arguments: dict):
    """
    MCP tool to remove a YouTube video.
    Required argument:
        - video_id: ID of the video to delete
    """
    video_id = arguments.get("video_id")
    if not video_id:
        return CallToolResult(
            content=[TextContent(type="text", text=":x: Missing 'video_id' argument")]
        )

    def delete_video_api(token):
        url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            return {"message": f":white_check_mark: Video '{video_id}' removed successfully!"}
        else:
            # Force raise error so wrapper can catch 401
            response.raise_for_status()

    try:
        result = call_youtube_api(delete_video_api)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        )
    except requests.exceptions.HTTPError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f":x: Failed to remove video: {e.response.text}")]
        )
    

if __name__ == "__main__":
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()


