#!/usr/bin/env python3
import json
from pathlib import Path

from jobhunt_api.main import app

out = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "lib" / "api" / "openapi.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"wrote {out}")
