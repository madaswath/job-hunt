#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from jobhunt_api.main import app

path = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "lib" / "api" / "openapi.json"
current = json.dumps(app.openapi(), indent=2) + "\n"
if not path.exists() or path.read_text() != current:
    print("OpenAPI drift. Run: python scripts/export_openapi.py")
    sys.exit(1)
print("OpenAPI in sync")
