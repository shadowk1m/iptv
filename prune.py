#!/usr/bin/env python3
"""Remove entries whose stream URL is not 'reachable' per scan-results.csv.

Keeps any channel with at least one reachable URL; pruned entries with a
reachable duplicate under the same tvg-name lose only their failing variant.
Originals remain in raw/ and in git history.        Run scan.py first.

Usage: python3 prune.py
"""

import csv

BASE = "shaanxi-mobile-cdn.m3u"
SCAN = "scan-results.csv"


def main() -> None:
    status = {row["url"]: row["status"]
              for row in csv.DictReader(open(SCAN, newline=""))}

    kept, removed = [], []
    pending = None
    for line in open(BASE, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            pending = line
            continue
        if pending is not None:
            st = status.get(line)
            if st == "reachable" or st is None:
                kept.extend([pending, line])
            else:
                name = pending.split(",")[-1] or pending
                removed.append(f"{name}  ->  {line}  [{st}]")
            pending = None
            continue
        kept.append(line)

    with open(BASE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")

    n = sum(1 for x in kept if x.startswith("#EXTINF"))
    print(f"kept {n} channels; removed {len(removed)}")
    for r in removed:
        print("  -", r)


if __name__ == "__main__":
    main()
