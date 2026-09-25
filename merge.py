#!/usr/bin/env python3
"""Merge raw/lingbaoboy-tv2.m3u into shaanxi-mobile-cdn.m3u (priority source).

For channels present in both lists, the lingbaoboy stream URL and logo win
(more stable source / faster logo host). lingbaoboy-only channels are appended.

Idempotent: re-running against an already-merged base makes no changes.
The base list is rewritten in place; run this before make-catchup.py.

Usage: python3 merge.py
"""

import re

BASE = "shaanxi-mobile-cdn.m3u"
EXTRA = "raw/lingbaoboy-tv2.m3u"
EPG = "https://epg.112114.xyz/pp.xml.gz"

# lingbaoboy uses a non-standard EXTINF form with its attributes after the
# first comma:  #EXTINF:-1,tvg-id="X" tvg-name="X" tvg-logo="…" group-title="G",Name
EXTRA_RE = re.compile(
    r'^#EXTINF:-1\s*,\s*tvg-id="[^"]*"\s*tvg-name="(?P<name>[^"]*)"\s*'
    r'tvg-logo="(?P<logo>[^"]*)"\s*group-title="(?P<group>[^"]*)"\s*,(?P<disp>.*)$'
)
NAME_RE = re.compile(r'tvg-name="([^"]*)"')
LOGO_RE = re.compile(r'tvg-logo="[^"]*"')

GROUP_MAP = {"央视": "央视频道", "卫视": "卫视频道", "其他": "综合其他"}


def parse_extra() -> list[tuple[str, str, str, str, str]]:
    """(tvg_name, logo, group, display_name, url) for each lingbaoboy entry."""
    items, pending = [], None
    for line in open(EXTRA, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            m = EXTRA_RE.match(line)
            pending = m.groupdict() if m else None
        elif pending and line.startswith("http"):
            group = "4K专区" if pending["name"].endswith("4K") else GROUP_MAP.get(
                pending["group"], "综合其他"
            )
            items.append((pending["name"], pending["logo"], group, pending["disp"], line))
            pending = None
    return items


def parse_base() -> list[list[str | None]]:
    """Blocks of [extinf, url]; non-channel lines are [line, None]."""
    blocks, pending = [], None
    for line in open(BASE, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#EXTINF"):
            pending = line
        elif pending is not None:
            blocks.append([pending, line])
            pending = None
        else:
            blocks.append([line, None])
    if pending:
        blocks.append([pending, None])
    return blocks


def main() -> None:
    extra = parse_extra()
    blocks = parse_base()

    # Index base channels by tvg-name.
    index = {}
    for i, (extinf, url) in enumerate(blocks):
        if extinf and url:
            m = NAME_RE.search(extinf)
            if m:
                index.setdefault(m.group(1), i)

    matched, added = 0, 0
    for name, logo, group, disp, url in extra:
        if name in index:
            i = index[name]
            blocks[i][0] = LOGO_RE.sub(f'tvg-logo="{logo}"', blocks[i][0])
            blocks[i][1] = url
            matched += 1

    # Append lingbaoboy-only channels.
    existing = set(index)
    inserts = []
    for name, logo, group, disp, url in extra:
        if name in existing:
            continue
        extinf = (
            f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" '
            f'group-title="{group}",{disp}'
        )
        inserts.append([extinf, url])
        existing.add(name)
        added += 1

    # Keep the EPG hint in the header, and place new channels before the last
    # line if the file ends with a newline-only entry.
    for b in blocks:
        if b[0] and b[0].startswith("#EXTM3U"):
            b[0] = f'#EXTM3U x-tvg-url="{EPG}"'
            break
    blocks.extend(inserts)

    with open(BASE, "w", encoding="utf-8") as f:
        f.write("\n".join(b[0] if b[1] is None else f"{b[0]}\n{b[1]}" for b in blocks) + "\n")

    total = sum(1 for e, u in blocks if e and u)
    print(f"merged: {matched} channels updated, {added} added, {total} total")


if __name__ == "__main__":
    main()
