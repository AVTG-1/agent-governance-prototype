"""Key views (SPEC §5.8): the last completed run's events, kept in memory, and the offline export.

A key view is just a position in the event log: the console folds events up to the k-th
`keyview` marker and renders with animations off. No snapshots, screenshots or second renderer.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime

from app.settings import WEB_DIR

SAFE_KINDS = ("run", "act", "caption", "panel", "map", "decision", "call", "llm", "system", "keyview")


class KeyViews:
    def __init__(self) -> None:
        self.meta: dict | None = None
        self.events: list[dict] = []

    @property
    def available(self) -> bool:
        return self.meta is not None

    def save(self, run) -> None:
        """Called when a run reaches the close card (and again when it ends). Replaces any earlier recording."""
        self.events = [dict(e) for e in run.events if e["kind"] in SAFE_KINDS]
        self.meta = {
            "run_id": run.id,
            "recorded_at": run.started_at.isoformat(timespec="minutes"),
            "agent_model": run.models.get("agent"),
            "investigator_model": run.models.get("investigator"),
            "plan_source": run.data.get("plan_source"),
        }

    def listing(self) -> dict:
        markers = [{**e["payload"], "seq": e["seq"], "ts": e["ts"]} for e in self.events if e["kind"] == "keyview"]
        return {"meta": self.meta, "views": markers, "events": self.events}

    def export_html(self) -> tuple[str, str]:
        """(filename, html): one self-contained file, offline, playback only, no token or settings."""
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        tokens = (WEB_DIR / "tokens.css").read_text(encoding="utf-8")
        styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
        app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
        styles = re.sub(r"url\((['\"]?)fonts/([^'\")]+)\1\)", _font_data_url, styles)
        html = re.sub(r"<!--gate-->.*?<!--/gate-->", "", html, flags=re.S)
        html = html.replace('<link rel="stylesheet" href="tokens.css">', f"<style>\n{tokens}\n</style>")
        html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>\n{styles}\n</style>")
        replay = json.dumps({"meta": self.meta, "events": self.events}, ensure_ascii=False).replace("</", "<\\/")
        app_js = app_js.replace("</script", "<\\/script")
        html = html.replace('<script type="module" src="app.js"></script>',
                            "<script>window.__REPLAY__ = " + replay + ";</script>\n"
                            '<script type="module">\n' + app_js + "\n</script>")
        stamp = datetime.fromisoformat(self.meta["recorded_at"]).strftime("%Y%m%d-%H%M")
        return f"key-views-{stamp}.html", html


def _font_data_url(m: re.Match) -> str:
    data = base64.b64encode((WEB_DIR / "fonts" / m.group(2)).read_bytes()).decode()
    return f"url(data:font/woff;base64,{data})"
