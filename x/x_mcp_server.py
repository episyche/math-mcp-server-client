from __future__ import annotations

import base64
import os

import requests
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

TOKEN=os.getenv("X_TOKEN")
BEARER_TOKEN=os.getenv("X_BEARER_TOKEN")
REFRESH_TOKEN=os.getenv("X_REFRESH_TOKEN")

# Default to public Twitter API base if not provided
BASE_URL=os.getenv("X_BASE_URL") or "https://api.twitter.com"
API_VERSION = "2"
CLIENT_ID=os.getenv("X_CLIENT_ID")
CLIENT_SECRET=os.getenv("X_CLIENT_SECRET")


mcp = FastMCP("XServer")


def _url(path):
    return f"{BASE_URL}/{API_VERSION}{path}"

def refresh_authorization():
    global TOKEN, REFRESH_TOKEN
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    credentials_bytes = credentials.encode("utf-8")
    b64_credentials = base64.b64encode(credentials_bytes).decode()
    headers = {
    "Authorization": f"Basic {b64_credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN
    }
    response = requests.post(_url("/oauth2/token"), data=data, headers=headers)
    if(response.status_code == 200):
        authentication_data = response.json()
        
        new_access = authentication_data["access_token"]
        new_refresh = authentication_data.get("refresh_token", REFRESH_TOKEN)

        TOKEN = new_access
        REFRESH_TOKEN = new_refresh
        # Persist to our server-local .env
        try:
            set_key(ENV_PATH, "TOKEN", new_access)
            set_key(ENV_PATH, "X_REFRESH_TOKEN", new_refresh)
        except Exception:
            pass

@mcp.tool()
def create_post(a: str):
    data = {
        "text": a,
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(_url("/tweets"), json=data, headers=headers)
    if response.status_code == 401:
        refresh_authorization()
        return create_post(a)
    # Twitter API v2 returns 201 for successful tweet creation
    try:
        response.raise_for_status()
    except Exception:
        # Return detailed error payload to the caller for diagnosics
        try:
            return {"status": response.status_code, "error": response.json()}
        except Exception:
            return {"status": response.status_code, "error": response.text}
    return response.json()

@mcp.tool()
def delete_post(a:str): 
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.delete(_url(f"/tweets/{a}"), headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return delete_post(a)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def get_post_by_id(a:str): 
    app_header={"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(_url(f"/tweets/{a}"), headers=app_header)
    if(response.status_code == 401):
        refresh_authorization()
        return get_post_by_id(a)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def get_my_user_info():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(_url("/users/me"), headers=headers)
    if(response.status_code==200):
        source_user_details = response.json()
    elif (response.status_code==401):
        refresh_authorization()
        return get_my_user_info()
    response.raise_for_status()
    return source_user_details

@mcp.tool()
def get_all_post_of_user(a:str):
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(_url(f"/users/{a}/tweets"), headers=headers)
        if(response.status_code == 401):
            refresh_authorization()
            return get_all_post_of_user(a)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching posts for user {a}: {e}")

@mcp.tool()
def get_user_by_username(a:str):
    app_header={"Authorization": f"Bearer {BEARER_TOKEN}"}
    target_user_response = requests.get(_url(f"/users/by/username/{a}"), headers=app_header)
    if(target_user_response.status_code==200):
        target_user_details = target_user_response.json()
    elif(target_user_response.status_code == 401):
        refresh_authorization()
        return get_user_by_username(a)
    target_user_response.raise_for_status()
    return target_user_details
    

@mcp.tool()
def follow_user(a: str, b:str):
    # source_user_id= "1956328951502278656"
    # target_user_id = "736267842681602048"
    data={
        "target_user_id":a
    }
    headers = {"Authorization": f"Bearer {TOKEN}"}    
    response = requests.post(_url(f"/users/{b}/following"), json=data, headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return follow_user(a)
    response.raise_for_status()    
    return response.json()

@mcp.tool()
def unfollow_user(a:str, b:str):
    # source_user_id= "1956328951502278656"
    # target_user_id = "736267842681602048"
    headers = {"Authorization": f"Bearer {TOKEN}"} 
    response = requests.delete(_url(f"/users/{b}/following/{a}"), headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return unfollow_user(a)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def recent_post_by_query(a:str):
    app_header={"Authorization": f"Bearer {BEARER_TOKEN}"}
    recent_search_info = requests.get(_url(f"/tweets/search/recent?max_results=10&query={a}"), headers=app_header)
    if(recent_search_info.status_code == 401):
        refresh_authorization()
        return recent_post_by_query(a)
    recent_search_info.raise_for_status()
    return recent_search_info.json()

@mcp.tool()
def like_post(a:str, b:str): 
    # source_user_id= "1956328951502278656"
    payload = { "tweet_id": a }
    headers = {"Authorization": f"Bearer {TOKEN}"} 
    response = requests.post(_url(f"/users/{b}/likes"), json=payload, headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return like_post(a)
    response.raise_for_status()
    return response.json()

@mcp.tool()
def unlike_post(a:str, b:str): 
    # source_user_id= "1956328951502278656"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.delete(_url(f"/users/{a}/likes/{b}"), headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return unlike_post(a)
    response.raise_for_status()
    return response.json()

@mcp.tool() 
def get_liked_post_of_user(a:str): 
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(_url(f"/users/{a}/liked_tweets"), headers=headers)
    if(response.status_code == 401):
        refresh_authorization()
        return get_liked_post_of_user(a)
    response.raise_for_status()
    return response.json()

@mcp.tool() 
def recent_post_count_by_query(a:str):
    app_header={"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(_url(f"/tweets/counts/recent?granularity=hour&query={a}"), headers=app_header)
    if(response.status_code == 401):
        refresh_authorization()
        return recent_post_count_by_query(a)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()


    