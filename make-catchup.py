#!/usr/bin/env python3
"""Generate shaanxi-mobile-cdn-catchup.m3u from shaanxi-mobile-cdn.m3u.

Adds per-channel catch-up (回看) attributes so players with an EPG offer
guide-based point-in-time replay. Each PLTV channel gets a catchup-source
template pointing at the TVOD endpoint; the player substitutes:

    ${(b)yyyyMMddHHmmss}  programme start time (from the EPG)
    ${(e)yyyyMMddHHmmss}  programme end time   (from the EPG)

This `${(b)...}/${(e)...}` convention is understood by TiviMate, DIYP/百川,
APTV and TVBox-family players. Kodi's IPTV Simple Client uses its own
specifiers ({utc}/{end} with format strings) — the -kodi variant below.

Also rewrites tvg-logo URLs from the dead `live.fanmingming.com` host to the
`fanmingming/live` GitHub mirror (same files, see README).
"""

import re

SRC = "shaanxi-mobile-cdn.m3u"
DST = "shaanxi-mobile-cdn-catchup.m3u"
DAYS = 7  # days of catch-up advertised to players (server keeps 7)

DEAD_HOST = "https://live.fanmingming.com/"
LIVE_HOST = "https://gh-proxy.org/raw.githubusercontent.com/fanmingming/live/main/"

URL_RE = re.compile(
    r"^http://dbiptv\.sn\.chinamobile\.com/PLTV/([^/]+)/([^/]+)/([^/]+)/index\.m3u8$"
)

# Time-window templates understood by each family of players. The server's
# playseek format is yyyyMMddHHmmss-yyyyMMddHHmmss.
STYLES = {
    # TiviMate / DIYP / 百川 / APTV / TVBox: programme start/end placeholders.
    "default": "${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}",
    # Kodi PVR IPTV Simple Client: {utc}/{end} with a format-string argument.
    "kodi": "{utc:YmdHMS}-${end:YmdHMS}",
}


def extinf_with_catchup(extinf: str, url: str, playseek: str) -> str:
    icpid, trans, chan = URL_RE.match(url).groups()
    tvod = f"http://dbiptv.sn.chinamobile.com/TVOD/{icpid}/{trans}/{chan}/index.m3u8"
    attrs = (
        'catchup="default" '
        f'catchup-source="{tvod}?playseek={playseek}" '
        f'tvg-rec="{DAYS}" catchup-days="{DAYS}"'
    )
    # Insert right after the last quoted attribute (group-title="…"),
    # i.e. before the "," that starts the display name.
    head, _, tail = extinf.rpartition('"')
    return f'{head}" {attrs}{tail}'


def main() -> None:
    out = {"default": [], "kodi": []}
    pending = None  # EXTINF line waiting for its URL line
    for line in open(SRC, encoding="utf-8"):
        line = line.rstrip("\n").replace(DEAD_HOST, LIVE_HOST)
        if line.startswith("#EXTINF"):
            pending = line
            continue
        if pending is not None:
            m = URL_RE.match(line)
            for style in out:
                if m:
                    out[style].append(extinf_with_catchup(pending, line, STYLES[style]))
                else:
                    out[style].append(pending)
            pending = None
        for style in out:
            out[style].append(line)

    for style, lines in out.items():
        dst = DST if style == "default" else DST.replace(".m3u", "-kodi.m3u")
        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        n = sum(1 for x in lines if x.startswith("#EXTINF") and "catchup-source" in x)
        print(f"wrote {dst}: {n} channels with catch-up")


if __name__ == "__main__":
    main()
