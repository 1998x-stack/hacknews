"""Minimal /healthz HTTP endpoint exposing last-success status."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


def build_status(config, ops, stale_hours: float = 48.0) -> dict:
    jobs = {}
    for job in config.jobs:
        jobs[job.name] = {
            "last_success": ops.last_status(job.name),
            "stale_seconds": round(ops.staleness_seconds(job.name, stale_hours), 1),
        }
    return {"ok": True, "jobs": jobs}


class HealthHandler(BaseHTTPRequestHandler):
    config = None
    ops = None
    stale_hours = 48.0

    def do_GET(self):
        if self.path != "/healthz":
            self.send_error(404)
            return
        body = json.dumps(build_status(self.config, self.ops, self.stale_hours)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence request logging
        pass


def start_health_server(config, ops, port: int = 8080, stale_hours: float = 48.0) -> HTTPServer:
    HealthHandler.config = config
    HealthHandler.ops = ops
    HealthHandler.stale_hours = stale_hours
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
