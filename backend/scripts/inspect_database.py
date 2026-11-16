"""Inspect the connected Supabase project without printing secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
GEMINI = os.environ.get("GEMINI_API_KEY", "")


def main() -> int:
    if not URL or not KEY:
        print("MISSING_SUPABASE_ENV")
        return 1
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/openapi+json",
    }
    report: dict = {"supabase_host": URL.split("//")[-1], "tables": {}, "gemini_models": []}
    with httpx.Client(timeout=40.0) as client:
        spec = client.get(f"{URL}/rest/v1/", headers=headers)
        report["openapi_status"] = spec.status_code
        if spec.status_code == 200:
            data = spec.json()
            paths = data.get("paths", {})
            definitions = data.get("definitions") or data.get("components", {}).get("schemas", {})
            interesting = [
                name
                for name in paths
                if any(
                    token in name
                    for token in (
                        "knowledge",
                        "museumai",
                        "artifact",
                        "chunk",
                        "document",
                        "source",
                    )
                )
            ]
            report["interesting_paths"] = interesting
            for path in interesting:
                key = path.strip("/")
                schema = definitions.get(key) or definitions.get(key.split("/")[-1]) or {}
                props = schema.get("properties", {})
                report["tables"][key] = {
                    "columns": {
                        col: {
                            "type": meta.get("type"),
                            "format": meta.get("format"),
                            "description": meta.get("description"),
                        }
                        for col, meta in props.items()
                    }
                }
            for table in (
                "knowledge_documents",
                "knowledge_chunks",
                "museumai_artifacts",
                "museumai_chunks",
            ):
                row = client.get(
                    f"{URL}/rest/v1/{table}",
                    headers={**headers, "Accept": "application/json", "Prefer": "count=exact"},
                    params={"select": "*", "limit": "1"},
                )
                content_range = row.headers.get("content-range")
                report["tables"].setdefault(table, {})
                report["tables"][table]["probe_status"] = row.status_code
                report["tables"][table]["content_range"] = content_range
                if row.status_code == 200:
                    body = row.json()
                    report["tables"][table]["sample_keys"] = list(body[0].keys()) if body else []
                    report["tables"][table]["sample_count_returned"] = len(body)
                else:
                    report["tables"][table]["error"] = row.text[:500]

        if GEMINI:
            models = client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": GEMINI},
                params={"pageSize": 100},
            )
            report["gemini_status"] = models.status_code
            if models.status_code == 200:
                names = []
                for model in models.json().get("models", []):
                    name = model.get("name", "")
                    methods = model.get("supportedGenerationMethods") or model.get("supportedActions") or []
                    if any(token in name for token in ("gemini-3", "embedding", "embed")):
                        names.append({"name": name, "methods": methods})
                report["gemini_models"] = names
            else:
                report["gemini_error"] = models.text[:800]

    out = ROOT / "evaluation" / "schema_inspection.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"WROTE {out}")
    print("OPENAPI", report.get("openapi_status"))
    print("PATHS", ", ".join(report.get("interesting_paths") or []))
    for table, info in report.get("tables", {}).items():
        if "probe_status" in info:
            print(table, info.get("probe_status"), info.get("content_range"), info.get("sample_keys"))
    print("GEMINI", report.get("gemini_status"), "models", len(report.get("gemini_models") or []))
    for model in report.get("gemini_models") or []:
        print(model["name"], ",".join(model["methods"]))
    if report.get("gemini_error"):
        print("GEMINI_ERROR", report["gemini_error"][:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
