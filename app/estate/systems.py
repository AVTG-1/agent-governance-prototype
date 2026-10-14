"""The simulated Kaiyo Securities systems: tiny functions over JSON fixtures.

Each run gets a fresh `Estate` so restart puts every system back to its seeded state.
Systems do not enforce anything; that is the control plane's job. In "today mode" agents
call these functions directly, which is exactly the problem the demo shows.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache

from app.settings import DATA_DIR

SYSTEMS = {
    "trade": {"name": "Trade capture", "interface": "REST API", "sensitive": "positions"},
    "settlement": {"name": "Settlement and SSIs", "interface": "REST API", "sensitive": "settlement instructions"},
    "recon": {"name": "Reconciliation", "interface": "Database", "sensitive": "breaks"},
    "client": {"name": "Client master", "interface": "Database", "sensitive": "PII: tax_id, email, dob"},
    "refdata": {"name": "Reference data", "interface": "REST API", "sensitive": "none"},
    "ledger": {"name": "General ledger", "interface": "Batch file", "sensitive": "quarter-end balances"},
    "external": {"name": "Outside the firm", "interface": "Internet", "sensitive": "—"},
}

PII_FIELDS = frozenset({"tax_id", "email", "dob"})
EXTERNAL_HOST = "diagnostics.example.invalid"


@lru_cache(maxsize=None)
def _load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load(name: str):
    """A private copy of a fixture file."""
    return copy.deepcopy(_load(name))


def mask(value: str) -> str:
    return "••••" + str(value)[-2:] if value else value


class Estate:
    """Fresh, mutable copy of every system for one run."""

    def __init__(self) -> None:
        self.trades = {t["trade_id"]: t for t in load("trades.json")}
        self.settlements = {s["trade_id"]: s for s in load("settlements.json")}
        self.breaks = {b["break_id"]: b for b in load("breaks.json")}
        clients = load("clients.json")
        self.column_tags = clients["column_tags"]
        self.clients = {c["client_id"]: c for c in clients["rows"]}
        self.ledger = load("ledger.json")
        self.refdata = load("refdata.json")
        self.outbox: list[dict] = []        # what reached "external"
        self.exports: list[dict] = []       # what reached the shared file drive

    # --- reads -------------------------------------------------------------------------
    def trade_read(self, trade_id: str) -> dict:
        return dict(self.trades.get(trade_id, {"error": f"no trade {trade_id}"}))

    def settlement_read(self, trade_id: str) -> dict:
        return dict(self.settlements.get(trade_id, {"error": f"no settlement for {trade_id}"}))

    def client_read(self, client_id: str, fields: list[str], *, reveal_pii: bool) -> dict:
        row = self.clients.get(client_id)
        if row is None:
            return {"error": f"no client {client_id}"}
        fields = fields or ["client_id", "name", "country"]
        out = {}
        for f in fields:
            if f not in row:
                continue
            out[f] = row[f] if (reveal_pii or f not in PII_FIELDS) else mask(row[f])
        return out

    def refdata_read(self, key: str = "calendar") -> dict:
        return {key: self.refdata.get(key)}

    def ledger_read_quarter_end(self) -> dict:
        return self.ledger

    # --- writes ------------------------------------------------------------------------
    def settlement_update(self, trade_id: str, status: str) -> dict:
        if trade_id in self.settlements:
            self.settlements[trade_id]["status"] = status
        return {"trade_id": trade_id, "status": status}

    def recon_update_break(self, break_id: str, status: str, note: str = "") -> dict:
        if break_id in self.breaks:
            self.breaks[break_id]["status"] = status
        return {"break_id": break_id, "status": status}

    def external_post(self, url: str, body: dict) -> dict:
        self.outbox.append({"url": url, "body": body})
        return {"status": 200, "received_fields": sorted(body)}

    def fileshare_export(self, rows: int, fields: list[str]) -> dict:
        self.exports.append({"rows": rows, "fields": fields})
        return {"exported_rows": rows}

    # --- one dispatcher, used by both the gateway and today mode -----------------------
    def execute(self, capability: str, args: dict, fields: list[str]) -> dict:
        a = args or {}
        if capability == "trade.read":
            return self.trade_read(a.get("trade_id", "T-1097"))
        if capability == "settlement.read":
            return self.settlement_read(a.get("trade_id", "T-1097"))
        if capability in ("client.read_masked", "client.read_pii"):
            return self.client_read(a.get("client_id", "C-102"), fields, reveal_pii=capability == "client.read_pii")
        if capability == "refdata.read":
            return self.refdata_read(a.get("key", "calendar"))
        if capability == "ledger.read_quarter_end":
            return self.ledger_read_quarter_end()
        if capability == "settlement.update":
            return self.settlement_update(a.get("trade_id", "T-1097"), a.get("status", "pending"))
        if capability == "recon.update":
            return self.recon_update_break(a.get("break_id", "RC-90031"), a.get("status", "investigating"))
        if capability == "external.post":
            return self.external_post(a.get("url", f"https://{EXTERNAL_HOST}/resolve"), a.get("body", {}))
        if capability == "fileshare.export":
            return self.fileshare_export(int(a.get("rows", 1)), fields)
        if capability == "ssi.amend":
            return {"trade_id": a.get("trade_id"), "amended": True}
        if capability == "fx.read":
            return {"fx_positions": "…"}
        return {"error": f"unknown capability {capability}"}
