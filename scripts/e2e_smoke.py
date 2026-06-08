import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_KEY = os.environ.get("API_KEY", "dev-api-key")
BASE_URL = os.environ.get("FOLIUN_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    """Run a lightweight end-to-end smoke test against a running API server."""

    sample = ROOT / "storage" / "e2e_sample.txt"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text("Foliun uses local BGE embeddings and Ollama for grounded document answers. " * 80, encoding="utf-8")
    with httpx.Client(timeout=30) as client:
        health = client.get(f"{BASE_URL}/api/v1/health")
        print("health", health.status_code, health.text)
        with sample.open("rb") as handle:
            upload = client.post(
                f"{BASE_URL}/api/v1/documents",
                headers={"X-API-Key": API_KEY},
                files={"file": ("e2e_sample.txt", handle, "text/plain")},
            )
        print("upload", upload.status_code, upload.text)
        upload.raise_for_status()
        payload = upload.json()
        document_id = payload["document_id"]
        status_url = f"{BASE_URL}/api/v1/documents/{document_id}/status"
        for _ in range(60):
            status = client.get(status_url, headers={"X-API-Key": API_KEY})
            print("status", status.status_code, status.text)
            if status.json()["status"] in {"ready", "failed"}:
                break
            time.sleep(1)
        too_long = client.post(f"{BASE_URL}/api/v1/query", headers={"X-API-Key": API_KEY}, json={"query": "x" * 2001})
        print("too_long", too_long.status_code, too_long.text)
        missing_auth = client.get(f"{BASE_URL}/api/v1/documents")
        print("missing_auth", missing_auth.status_code, missing_auth.text)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
