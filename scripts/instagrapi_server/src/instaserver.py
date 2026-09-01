"""https://subzeroid.github.io/instagrapi/

Run using the following command:
 uvicorn src.instaserver:app --port 8000 --reload
"""

import logging
import os
import secrets
import sys
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadCredentials

load_dotenv(dotenv_path="secrets/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
INSTAGRAPI_API_KEY = os.getenv("INSTAGRAPI_API_KEY")
SESSION_FILE = "secrets/instagrapi_session.json"

# The auto-archiver instagram_api_extractor sends its access_token in this header.
api_key_header = APIKeyHeader(name="x-access-key", auto_error=False)


def verify_access_key(provided_key: str = Security(api_key_header)):
    """Rejects any request that does not carry the configured API key."""
    if not INSTAGRAPI_API_KEY or not provided_key or not secrets.compare_digest(provided_key, INSTAGRAPI_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key (x-access-key header)")


app = FastAPI(dependencies=[Depends(verify_access_key)])
cl = Client()


@app.on_event("startup")
def startup_event():
    """Login automatically when server starts"""
    if not INSTAGRAPI_API_KEY:
        logging.error(
            "INSTAGRAPI_API_KEY is not set. Refusing to start an unauthenticated server: "
            "add INSTAGRAPI_API_KEY=<random secret> to secrets/.env and use the same value "
            "as the instagram_api_extractor 'access_token' in your orchestration file."
        )
        sys.exit(1)
    try:
        login_instagram()
    except RuntimeError as e:
        logging.error(f"API failed to start: {e}")
        sys.exit(1)


def login_instagram():
    """Ensures Instagrapi is logged in and session is persistent"""
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise RuntimeError("Instagram credentials are missing.")

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            logging.info("Using saved session.")
            return
        except LoginRequired:
            logging.info("Session expired. Logging in again...")

    try:
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        os.chmod(SESSION_FILE, 0o600)
        logging.info("Login successful, session saved.")
    except BadCredentials as bc:
        raise RuntimeError("Incorrect Instagram username or password.") from bc
    except Exception as e:
        raise RuntimeError(f"Login failed: {e}") from e


@app.get("/v1/media/by/id")
def get_media_by_id(id: str):
    """Fetch post details by media ID"""
    logging.info(f"Fetching media by ID: {id}")
    try:
        media = cl.media_info(id)
        return media.model_dump()
    except Exception as e:
        logging.warning(f"Media not found for ID {id}: {e}")
        raise HTTPException(status_code=404, detail="Post not found") from e


@app.get("/v1/media/by/code")
def get_media_by_code(code: str):
    """Fetch post details by shortcode"""
    logging.info(f"Fetching media by shortcode: {code}")
    try:
        media_id = cl.media_pk_from_code(code)
        media = cl.media_info(media_id)
        return media.model_dump()
    except Exception as e:
        logging.warning(f"Media not found for code {code}: {e}")
        raise HTTPException(status_code=404, detail="Post not found") from e


@app.get("/v2/user/tag/medias")
def get_user_tagged_medias(user_id: str, page_id: str = None):
    logging.info(f"Fetching tagged medias for user_id={user_id} page_id={page_id}")
    try:
        # Placeholder for now
        items, next_page_id = [], None
        return {"response": {"items": items}, "next_page_id": next_page_id}
    except Exception as e:
        logging.warning(f"Tagged media not found for {user_id}: {e}")
        raise HTTPException(status_code=404, detail="Tagged media not found") from e


@app.get("/v1/user/highlights")
def get_user_highlights(user_id: str):
    logging.info(f"Fetching highlights list for user_id={user_id}")
    try:
        highlights = cl.user_highlights(user_id)
        return [h.model_dump() for h in highlights]
    except Exception as e:
        logging.warning(f"Highlights not found for {user_id}: {e}")
        raise HTTPException(status_code=404, detail="No highlights found") from e


@app.get("/v2/highlight/by/id")
def get_highlight_by_id(id: str):
    logging.info(f"Fetching highlight details for id={id}")
    try:
        highlight = cl.highlight_info(id)
        return {"response": {"reels": {f"highlight:{id}": highlight.model_dump()}}}
    except Exception as e:
        logging.warning(f"Highlight not found for id {id}: {e}")
        raise HTTPException(status_code=404, detail="Highlight not found") from e


@app.get("/v1/user/stories/by/username")
def get_stories(username: str):
    logging.info(f"Fetching stories for username={username}")
    try:
        user_id = cl.user_id_from_username(username)
        stories = cl.user_stories(user_id)
        return [story.model_dump() for story in stories]
    except Exception as e:
        logging.warning(f"Stories not found for {username}: {e}")
        raise HTTPException(status_code=404, detail="Stories not found") from e


@app.get("/v2/user/by/username")
def get_user_by_username(username: str):
    logging.info(f"Fetching user profile for username={username}")
    try:
        user = cl.user_info_by_username(username)
        return {"user": user.model_dump()}
    except Exception as e:
        logging.warning(f"User not found: {username}: {e}")
        raise HTTPException(status_code=404, detail="User not found") from e


@app.get("/v1/user/medias/chunk")
def get_user_medias(user_id: str, end_cursor: str = None):
    logging.info(f"Fetching paginated medias for user_id={user_id}, end_cursor={end_cursor}")
    try:
        posts, next_cursor = cl.user_medias_paginated(user_id, end_cursor=end_cursor)
        return [[post.model_dump() for post in posts], next_cursor]
    except Exception as e:
        logging.warning(f"No posts found for user_id={user_id}: {e}")
        raise HTTPException(status_code=404, detail="No posts found") from e


if __name__ == "__main__":
    import uvicorn

    # Bind to localhost by default; set HOST=0.0.0.0 explicitly (e.g. inside Docker,
    # where the port mapping controls external exposure) to listen on all interfaces.
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=8000)
