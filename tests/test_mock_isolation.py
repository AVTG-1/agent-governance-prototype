"""The mock LLM is for tests only: no application module imports it, and the app never loads it."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_app_module_imports_mock():
    offenders = []
    for p in list((ROOT / "app").rglob("*.py")) + [ROOT / "run.py"] + list((ROOT / "web").rglob("*.js")):
        if p.name == "mock.py":
            continue
        if re.search(r"(from\s+app\.llm\s+import\s+[^\n]*\bmock\b|app\.llm\.mock|import\s+mock\b|MockLLM)", p.read_text(encoding="utf-8")):
            offenders.append(str(p.relative_to(ROOT)))
    assert offenders == []


def test_app_never_loads_mock():
    code = ("import sys, app.main; from fastapi.testclient import TestClient; c = TestClient(app.main.app); "
            "[c.get(u) for u in ('/', '/api/catalog', '/api/connection/status')]; "
            "print('app.llm.mock' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.stdout.strip().endswith("False"), out.stderr
