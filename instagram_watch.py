#!/usr/bin/env python3
"""Daily Instagram watcher.

Reads the latest Instagram media item via Graph API and compares it against a
local state file. If there's a new post, prints a small JSON payload to stdout.

Outputs (stdout):
  {"new": true|false, "id": "...", "permalink": "...", "timestamp": "..."}

Exit codes:
  0 success (including no new post)
  2 misconfiguration/auth issue

Auth:
- Uses the same 1Password-backed token scheme as instagram_sync.py:
  - IG Graph token from op://OpenClaw/instagram-api-key-zachisntdead/credential
  - IG business account id from op://OpenClaw/instagram-api-key-zachisntdead/username

This script is designed to run under cron.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "instagram" / "last_seen.json"
GRAPH_BASE = "https://graph.facebook.com/v19.0"


def sh(*args: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), text=True, check=check, capture_output=capture)


def _try_load_op_service_token_from_systemd_dropin() -> None:
    if os.environ.get("OP_SERVICE_ACCOUNT_TOKEN"):
        return
    dropin = Path.home() / ".config/systemd/user/openclaw-gateway.service.d/10-1password.conf"
    if not dropin.exists():
        return
    m = re.search(r'Environment="OP_SERVICE_ACCOUNT_TOKEN=([^"]+)"', dropin.read_text())
    if m:
        os.environ["OP_SERVICE_ACCOUNT_TOKEN"] = m.group(1)


def op_read(ref: str) -> str:
    _try_load_op_service_token_from_systemd_dropin()
    return sh("op", "read", ref, capture=True).stdout.strip()


def get_token_and_ig_id() -> tuple[str, str]:
    vault = os.environ.get("IG_OP_VAULT", "OpenClaw").strip()
    item = os.environ.get("IG_OP_ITEM", "instagram-api-key-zachisntdead").strip()

    token = os.environ.get("IG_GRAPH_ACCESS_TOKEN", "").strip() or op_read(f"op://{vault}/{item}/credential")
    ig_id = os.environ.get("IG_GRAPH_IG_USER_ID", "").strip() or op_read(f"op://{vault}/{item}/username")

    if not token or not ig_id:
        raise RuntimeError("missing token or ig user id")
    return token, ig_id


def graph_get_latest(token: str, ig_id: str) -> dict[str, Any]:
    # Use curl with -G + --data-urlencode to avoid token escaping issues.
    fields = "id,permalink,timestamp,media_type"
    out = sh(
        "curl",
        "-sS",
        "-G",
        f"{GRAPH_BASE}/{ig_id}/media",
        "--data-urlencode",
        f"fields={fields}",
        "--data-urlencode",
        "limit=1",
        "--data-urlencode",
        f"access_token={token}",
        capture=True,
    ).stdout

    data = json.loads(out)
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(str(data["error"]))
    items = (data.get("data") or [])
    return items[0] if items else {}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def main() -> None:
    try:
        token, ig_id = get_token_and_ig_id()
        latest = graph_get_latest(token, ig_id)
        latest_id = str(latest.get("id", ""))
        permalink = str(latest.get("permalink", ""))
        timestamp = str(latest.get("timestamp", ""))

        if not latest_id:
            print(json.dumps({"new": False}))
            return

        state = load_state()
        last_id = str(state.get("last_id", ""))

        is_new = last_id != latest_id and last_id != ""

        # Always update state to the latest we can see.
        save_state({"last_id": latest_id, "seen_at": dt.datetime.now(dt.timezone.utc).isoformat()})

        print(
            json.dumps(
                {
                    "new": bool(is_new),
                    "id": latest_id,
                    "permalink": permalink,
                    "timestamp": timestamp,
                }
            )
        )

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
