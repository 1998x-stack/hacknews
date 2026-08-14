"""Command-line entry points: run | doctor | readiness | serve."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from hacknews.config import load_config
from hacknews.email_sender import EmailSender
from hacknews.health import start_health_server
from hacknews.hn_client import HackerNewsClient
from hacknews.logging_setup import setup_logging
from hacknews.ops import OpsNotifier
from hacknews.pipeline import run_job
from hacknews.scheduler import create_scheduler

STALE_HOURS = 48.0
STATE_DIR = "state"


def parse_args(argv=None) -> argparse.Namespace:
    # --config must be accepted both before AND after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml")
    parser = argparse.ArgumentParser(prog="hacknews", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", parents=[common], help="run one digest job and exit")
    run_p.add_argument("job")
    sub.add_parser("serve", parents=[common], help="run cron scheduler and health server")
    sub.add_parser("doctor", parents=[common], help="validate config and report settings")
    sub.add_parser("readiness", parents=[common], help="report per-job last-success state")
    return parser.parse_args(argv)


def _secrets(env) -> dict:
    return {
        "host": env.get("SMTP_HOST"),
        "port": int(env.get("SMTP_PORT", "587")),
        "from_addr": env.get("EMAIL_FROM"),
        "password": env.get("EMAIL_FROM_PASSWORD"),
        "proxy": env.get("PROXY"),
    }


def _service(cfg, env):
    secrets = _secrets(env)
    hn = HackerNewsClient(proxy=secrets["proxy"])
    sender = EmailSender(
        secrets["host"], secrets["port"], secrets["from_addr"], secrets["password"]
    )
    ops = OpsNotifier(STATE_DIR, cfg.ops, email_sender=sender)
    return hn, sender, ops


def _find_job(cfg, name):
    return next((j for j in cfg.jobs if j.name == name), None)


def main(argv=None) -> int:
    args = parse_args(argv)
    env = os.environ
    cfg = load_config(args.config, env)
    setup_logging(cfg.settings.log_level)
    hn, sender, ops = _service(cfg, env)

    if args.command == "run":
        job = _find_job(cfg, args.job)
        if job is None:
            print(f"unknown job: {args.job}", file=sys.stderr)
            return 2
        try:
            run_job(cfg, job, hn, sender, ops)
        except Exception as exc:  # noqa: BLE001
            ops.notify_failure(job.name, str(exc))
            return 1
        return 0

    if args.command == "doctor":
        print(
            json.dumps(
                {
                    "ok": True,
                    "jobs": [j.name for j in cfg.jobs],
                    "recipients": [r.email for r in cfg.recipients],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "readiness":
        stale = [
            j.name
            for j in cfg.jobs
            if ops.staleness_seconds(j.name, STALE_HOURS) > STALE_HOURS * 3600
        ]
        print(json.dumps({"stale": stale}))
        return 1 if stale else 0

    if args.command == "serve":
        scheduler = create_scheduler(cfg, hn, sender, ops)
        scheduler.start()
        start_health_server(cfg, ops)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            scheduler.shutdown(wait=False)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
