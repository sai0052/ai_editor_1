# Updates aieditor.website DNS to Vercel.
# Reads GODADDY_PAT from backend/.godaddy.env

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / "backend" / ".godaddy.env"
DOMAIN = "aieditor.website"
BASE = f"https://api.godaddy.com/v1/domains/{DOMAIN}/records"


def load_pat() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GODADDY_PAT="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"GODADDY_PAT not found in {ENV_PATH}")


def request(method: str, url: str, pat: str, body: list | None = None) -> object | None:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode()) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc


def main() -> None:
    pat = load_pat()
    request(
        "PUT",
        f"{BASE}/A/@",
        pat,
        [
            {"data": "216.198.79.1", "ttl": 600},
            {"data": "64.29.17.1", "ttl": 600},
        ],
    )
    print("Updated A @ -> 216.198.79.1, 64.29.17.1")
    request(
        "PUT",
        f"{BASE}/CNAME/www",
        pat,
        [{"data": "cname.vercel-dns.com", "ttl": 600}],
    )
    print("Updated CNAME www -> cname.vercel-dns.com")
    records = request("GET", BASE, pat) or []
    for rec in records:
        if rec.get("type") in {"A", "CNAME"} and rec.get("name") in {"@", "www"}:
            print(f"{rec['type']:5} {rec['name']:3} -> {rec['data']} (ttl {rec.get('ttl')})")


if __name__ == "__main__":
    main()
