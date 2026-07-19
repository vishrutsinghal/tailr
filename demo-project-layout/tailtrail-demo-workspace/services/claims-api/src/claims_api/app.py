from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from validation import validate_claim


ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "config" / "settings.json"


def load_settings() -> dict[str, Any]:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


class ClaimsHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/claims":
            self.respond(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.respond(400, {"errors": ["invalid json"]})
            return

        settings = load_settings()
        result = validate_claim(
            payload,
            allowed_types=set(settings["allowed_claim_types"]),
            max_amount=float(settings["max_claim_amount"]),
        )
        if not result.valid:
            self.respond(422, {"status": "rejected", "errors": result.errors})
            return

        self.respond(202, {"status": "accepted", "claim_id": payload["claim_id"]})

    def respond(self, status: int, body: dict[str, Any]) -> None:
        content = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    settings = load_settings()
    port = int(settings["port"])
    server = HTTPServer(("localhost", port), ClaimsHandler)
    print(f"claims-api-demo listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

