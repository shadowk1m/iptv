#!/usr/bin/env python3
"""Convert m3u playlists to DIYP/百川 txt format.

Reads shaanxi-mobile-cdn.m3u and shaanxi-mobile-xian-gitv.m3u and writes
DIYP-compatible txt files for each:

  <name>-diyp.txt          flat:      频道名,URL
  <name>-diyp-grouped.txt   grouped:  组名,#genre# header + 频道名,URL

DIYP/百川, PotPlayer, and many Chinese set-top boxes read this format.

Usage: python3 convert.py
"""

import re

SOURCES = ["shaanxi-mobile-cdn.m3u", "shaanxi-mobile-xian-gitv.m3u"]
GROUP_RE = re.compile(r'group-title="([^"]*)"')

# Remap our m3u group titles to DIYP-friendly Chinese names.
GROUP_MAP = {
    "4K专区": "4K", "央视频道": "央视", "卫视频道": "卫视",
    "体育频道": "体育", "影视剧场": "影视", "少儿频道": "少儿",
    "特色频道": "特色", "购物频道": "购物", "综合其他": "其他",
    "陕西·西安频道": "陕西", "凤凰中文台": "凤凰",
}


def parse(path: str) -> list[tuple[str, str, str]]:
    """(display_name, url, group) per channel."""
    items, pending = [], None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            pending = line
        elif pending and line.startswith("http"):
            name = pending.split(",", 1)[1] if "," in pending else ""
            m = GROUP_RE.search(pending)
            group = GROUP_MAP.get(m.group(1), "其他") if m else "其他"
            items.append((name, line, group))
            pending = None
    return items


def write_flat(items: list[tuple[str, str, str]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(f"{n},{u}" for n, u, _ in items) + "\n")


def write_grouped(items: list[tuple[str, str, str]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        last = None
        for n, u, g in items:
            if g != last:
                f.write(f"{g},#genre#\n")
                last = g
            f.write(f"{n},{u}\n")


def main() -> None:
    for src in SOURCES:
        items = parse(src)
        base = src.removesuffix(".m3u")
        write_flat(items, f"{base}-diyp.txt")
        write_grouped(items, f"{base}-diyp-grouped.txt")
        groups = {}
        for _, _, g in items:
            groups[g] = groups.get(g, 0) + 1
        print(f"{base}: {len(items)} channels across {len(groups)} groups")
        for g, n in sorted(groups.items(), key=lambda x: -x[1]):
            print(f"  {g:6s} {n}")


if __name__ == "__main__":
    main()