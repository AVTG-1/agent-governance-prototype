"""Start the demo: python run.py  (opens http://127.0.0.1:8765 in the browser)."""
from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.settings import HOST, PORT


def main() -> None:
    url = f"http://{HOST}:{PORT}/"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"Agent governance demo on {url}  (Ctrl+C to stop)")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
