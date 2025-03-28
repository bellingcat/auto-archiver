"""https://subzeroid.github.io/instagrapi/

Run using the following command:
 uvicorn src.instgrapinstance.instaserver:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
import sys
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadCredentials

load_dotenv(dotenv_path="secrets/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
SESSION_FILE = "secrets/instagrapi_session.json"

app = FastAPI()
cl = Client()


@app.on_event("startup")
def startup_event():
    """Login automatically when server starts"""
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
