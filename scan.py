#!/usr/bin/env python3
"""Detect unreachable stream URLs in the m3u playlists.

Classification (per URL):
  reachable   HTTP 200 with body, anywhere
  intranet   404/302→empty on a China Mobile IP block — likely works on CMCC broadband
  dead       4xx/5xx on a public IP, or persistent error — safe to remove
  error      connect failure / timeout — likely dead

Run `python3 scan.py` to print a summary and write `scan-results.csv`.
Edit the `categorize()` rule + the `remove.py` step manually if you disagree.
"""

import concurrent.futures
import csv
import ipaddress
import socket
import subprocess
import sys
from collections import Counter
from urllib.parse import urlparse

FILES = ["shaanxi-mobile-cdn.m3u", "shaanxi-mobile-xian-gitv.m3u"]

# China Mobile (AS 9808) IP blocks — heuristics, not exhaustive.
CMCC_NETS = [
    ipaddress.ip_network(n) for n in
    ["111.0.0.0/8", "39.128.0.0/9", "39.192.0.0/10", "117.128.0.0/9",
     "120.192.0.0/10", "36.0.0.0/10", "120.80.0.0/13"]
]

# Hosts the user has flagged as intranet-only in the README.
KNOWN_INTRANET_HOSTS = {"211.137.115.110"}

TIMEOUT_S = 8
WORKERS = 15


def extract_urls() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for f in FILES:
        pending = False
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line.startswith("#EXTINF"):
                pending = True
            elif pending and line.startswith("http"):
                out.setdefault(line, set()).add(f)
                pending = False
    return out


def dns_ip(url: str) -> str:
    try:
        host = urlparse(url).hostname
        if host is None:
            return ""
        # ip literal → return as-is
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            return socket.gethostbyname(host)
    except Exception:
        return ""


def test_url(url: str) -> list[str]:
    try:
        r = subprocess.run(
            ["curl", "-sSL", "-m", str(TIMEOUT_S), "-o", "/dev/null",
             "-w", "%{http_code}|%{url_effective}|%{remote_ip}|%{size_download}",
             url],
            capture_output=True, text=True, timeout=TIMEOUT_S + 4,
        )
        return r.stdout.strip().split("|", 3)
    except subprocess.TimeoutExpired:
        return ["000", "TIMEOUT", "", "0"]
    except Exception as e:
        return ["000", "ERR", str(e), "0"]


def categorize(code: str, ip: str, size: str, host: str) -> str:
    try:
        code_i = int(code)
    except ValueError:
        return "error"
    if 200 <= code_i < 300 and int(size) > 0:
        return "reachable"
    # explicit intranet overrides
    if host in KNOWN_INTRANET_HOSTS:
        return "intranet"
    try:
        ipa = ipaddress.ip_address(ip)
        cmcc = any(ipa in n for n in CMCC_NETS)
    except ValueError:
        cmcc = False
    if code_i in (0, 301, 302, 404, 403):
        return "intranet" if cmcc else "dead"
    if code_i >= 500:
        return "dead"
    return "unknown"


def main() -> None:
    urls = extract_urls()
    print(f"Testing {len(urls)} unique URLs across {len(FILES)} files "
          f"({WORKERS} parallel, {TIMEOUT_S}s timeout)", file=sys.stderr)

    # DNS resolution pass (uses system DNS, fast).
    dns = {u: dns_ip(u) for u in urls}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(lambda u: (u, *test_url(u)), urls))

    rows = []
    for u, code, final, ip, size in results:
        host = urlparse(u).hostname or ""
        effective_ip = ip or dns.get(u, "")
        status = categorize(code, effective_ip, size, host)
        rows.append((u, code, final, effective_ip, size, status))

    counts = Counter(r[5] for r in rows)
    print("\nStatus breakdown:", file=sys.stderr)
    for k, v in counts.most_common():
        print(f"  {k:9s} {v}", file=sys.stderr)

    print("\nSample per category:", file=sys.stderr)
    for cat in ["reachable", "intranet", "dead", "error", "unknown"]:
        for u, code, final, ip, size, _ in [r for r in rows if r[5] == cat][:3]:
            print(f"  [{cat:9s}] HTTP {code:>3}  ip={ip:15s}  {u}", file=sys.stderr)

    with open("scan-results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["url", "http_code", "final_url", "final_ip", "size", "status"])
        w.writerows(rows)
    print(f"\nFull results written to scan-results.csv", file=sys.stderr)


if __name__ == "__main__":
    main()