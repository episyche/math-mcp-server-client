import os
import base64
import requests
from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
print(ENV_PATH)
load_dotenv(ENV_PATH)

TOKEN=os.getenv("X_TOKEN")
BASE_URL=os.getenv("X_BASE_URL") or "https://api.twitter.com"
API_VERSION = "2"
CLIENT_ID=os.getenv("X_CLIENT_ID")
CLIENT_SECRET=os.getenv("X_CLIENT_SECRET")
REFRESH_TOKEN=os.getenv("X_REFRESH_TOKEN")
print(TOKEN)

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
            set_key(ENV_PATH, "REFRESH_TOKEN", new_refresh)
        except Exception:
            pass

def get_my_user_info():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    print(headers)
    response = requests.get(_url("/users/me"), headers=headers)
    print(response.status_code , response.text)
    if(response.status_code==200):
        source_user_details = response.json()
    elif (response.status_code==401):
        refresh_authorization()
        return get_my_user_info()
    response.raise_for_status()
    return source_user_details

get_my_user_info()