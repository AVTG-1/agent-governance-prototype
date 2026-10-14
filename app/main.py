"""HTTP routes. One process: API, SSE stream and the static console."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.settings import WEB_DIR

app = FastAPI(title="Agent governance demo", docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
