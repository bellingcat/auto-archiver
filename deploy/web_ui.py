#!/usr/bin/env python3
"""
Minimal web UI for auto-archiver cloud deployments.

Provides:
  - GET  /          → HTML form to submit URLs for archiving
  - POST /archive   → Runs auto-archiver on submitted URLs
  - GET  /results   → Lists archived files available for download
  - GET  /files/{path} → Serves archived files
  - GET  /status    → Health check
"""

import asyncio
import html
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")
ARCHIVE_DIR = Path("/app/local_archive")
CONFIG_PATH = Path("/app/secrets/orchestration.yaml")
COOKIE_NAME = "aa_session"

# In-memory session tokens (reset on restart, which is fine for this use case)
_valid_sessions: set[str] = set()
# In-memory job log
_jobs: list[dict] = []

app = FastAPI(title="Auto Archiver", docs_url=None, redoc_url=None)


# ── Auth helpers ──────────────────────────────────────────────────────


def _check_auth(request: Request):
    """Dependency: redirect to /login if auth is enabled and session is missing."""
    if not AUTH_PASSWORD:
        return  # auth disabled
    token = request.cookies.get(COOKIE_NAME, "")
    if token not in _valid_sessions:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )


# ── Pages ─────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auto Archiver – Login</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 420px; margin: 80px auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  input[type=password], button {{ font-size: 1rem; padding: .5rem .8rem; }}
  input[type=password] {{ width: 100%; box-sizing: border-box; margin: .5rem 0; }}
  button {{ cursor: pointer; background: #2563eb; color: #fff; border: none; border-radius: 4px; }}
  .err {{ color: #dc2626; }}
</style></head><body>
<h1>🔐 Auto Archiver</h1>
<form method="POST" action="/login">
  <label>Password<br><input type="password" name="password" autofocus required></label><br>
  <button type="submit">Log in</button>
  {error}
</form></body></html>"""


MAIN_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auto Archiver</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
  h1 {{ font-size: 1.5rem; }}
  textarea {{ width: 100%; box-sizing: border-box; font-size: .95rem; font-family: monospace; }}
  button {{ font-size: 1rem; padding: .5rem 1.2rem; cursor: pointer; background: #2563eb; color: #fff; border: none; border-radius: 4px; margin-top: .5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #e5e7eb; padding: .4rem .6rem; text-align: left; font-size: .9rem; }}
  th {{ background: #f9fafb; }}
  .status {{ padding: 2px 8px; border-radius: 4px; font-size: .85rem; }}
  .running {{ background: #fef3c7; color: #92400e; }}
  .done {{ background: #d1fae5; color: #065f46; }}
  .failed {{ background: #fee2e2; color: #991b1b; }}
  a {{ color: #2563eb; }}
  .info {{ color: #6b7280; font-size: .9rem; }}
  nav {{ display: flex; gap: 1rem; align-items: center; }}
  nav a {{ text-decoration: none; }}
</style></head><body>
<nav>
  <h1>📦 Auto Archiver</h1>
  <a href="/results">Browse files</a>
  {logout}
</nav>
<form method="POST" action="/archive">
  <label for="urls"><strong>URLs to archive</strong> (one per line)</label><br>
  <textarea id="urls" name="urls" rows="5" placeholder="https://example.com/post&#10;https://youtube.com/watch?v=..." required></textarea><br>
  <button type="submit">Archive</button>
</form>
{jobs_html}
</body></html>"""


RESULTS_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auto Archiver – Files</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  a {{ color: #2563eb; }}
  li {{ margin: .3rem 0; font-family: monospace; font-size: .9rem; }}
</style></head><body>
<h1>📁 Archived Files</h1>
<p><a href="/">← Back</a></p>
{file_list}
</body></html>"""


# ── Routes ────────────────────────────────────────────────────────────


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    if not AUTH_PASSWORD:
        return RedirectResponse("/", status_code=302)
    return LOGIN_HTML.format(error="")


@app.post("/login")
async def login_submit(password: str = Form(...)):
    if not AUTH_PASSWORD:
        return RedirectResponse("/", status_code=302)
    if password != AUTH_PASSWORD:
        return HTMLResponse(
            LOGIN_HTML.format(error='<p class="err">Wrong password.</p>'),
            status_code=401,
        )
    token = secrets.token_urlsafe(32)
    _valid_sessions.add(token)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=86400 * 30)
    return resp


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(_check_auth)):
    logout = '<a href="/logout">Logout</a>' if AUTH_PASSWORD else ""
    jobs_html = _render_jobs()
    return MAIN_HTML.format(logout=logout, jobs_html=jobs_html)


@app.post("/archive")
async def archive(request: Request, urls: str = Form(...), _=Depends(_check_auth)):
    url_list = [u.strip() for u in urls.strip().splitlines() if u.strip()]
    if not url_list:
        raise HTTPException(400, "No URLs provided")

    job = {
        "id": len(_jobs) + 1,
        "urls": url_list,
        "status": "running",
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "output": "",
    }
    _jobs.insert(0, job)

    # Run in background so the user sees the page immediately
    asyncio.create_task(_run_archive(job))
    return RedirectResponse("/", status_code=303)


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request, _=Depends(_check_auth)):
    if not ARCHIVE_DIR.exists():
        return RESULTS_HTML.format(file_list="<p>No archived files yet.</p>")

    files = sorted(ARCHIVE_DIR.rglob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file()]

    if not files:
        return RESULTS_HTML.format(file_list="<p>No archived files yet.</p>")

    items = []
    for f in files[:200]:  # cap listing
        rel = f.relative_to(ARCHIVE_DIR)
        items.append(f'<li><a href="/files/{rel}">{html.escape(str(rel))}</a></li>')

    return RESULTS_HTML.format(file_list="<ul>" + "\n".join(items) + "</ul>")


@app.get("/files/{path:path}")
async def serve_file(path: str, request: Request, _=Depends(_check_auth)):
    full = ARCHIVE_DIR / path
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found")
    # Security: ensure the resolved path is within ARCHIVE_DIR
    try:
        full.resolve().relative_to(ARCHIVE_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")
    return FileResponse(full)


@app.get("/status")
async def health():
    return {"status": "ok"}


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME, "")
    _valid_sessions.discard(token)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ── Helpers ───────────────────────────────────────────────────────────


async def _run_archive(job: dict):
    """Run auto-archiver as a subprocess for the given URLs."""
    cmd = [
        "python3",
        "-m",
        "auto_archiver",
        "--config",
        str(CONFIG_PATH),
    ] + job["urls"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd="/app",
        )
        stdout, _ = await proc.communicate()
        job["output"] = stdout.decode(errors="replace")[-5000:]  # keep last 5k chars
        job["status"] = "done" if proc.returncode == 0 else "failed"
    except Exception as e:
        job["output"] = str(e)
        job["status"] = "failed"


def _render_jobs() -> str:
    if not _jobs:
        return '<p class="info">No archiving jobs yet. Submit URLs above to get started.</p>'

    rows = []
    for j in _jobs[:50]:
        urls_str = html.escape(", ".join(j["urls"][:3]))
        if len(j["urls"]) > 3:
            urls_str += f" (+{len(j['urls']) - 3} more)"
        status_cls = j["status"]
        rows.append(
            f"<tr><td>{j['id']}</td>"
            f"<td>{urls_str}</td>"
            f'<td><span class="status {status_cls}">{j["status"]}</span></td>'
            f"<td>{j['started']}</td></tr>"
        )

    return (
        "<h2>Recent Jobs</h2>"
        "<table><thead><tr><th>#</th><th>URLs</th><th>Status</th><th>Started</th></tr></thead>"
        "<tbody>" + "\n".join(rows) + "</tbody></table>"
    )
