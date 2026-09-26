# Self-contained image with the playlists baked in.
# The LAN host needs no repo checkout or scripts — just the image.
#
#   docker build -t iptv:latest .
#   docker run -d -p 8080:80 --name iptv iptv:latest
#
# Regenerate playlists first if needed (make-catchup.py / convert.py),
# then rebuild. If you prefer zero-rebuild updates instead, run the
# bind-mounted compose variant (see compose.yaml) which mounts ./ over
# /srv/iptv and shadows these baked copies at runtime.

FROM nginx:alpine

# Short-URL aliases (/iptv.txt, /catchup.m3u, ...) + block non-playlist paths
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Master + derived playlists, matching the paths in nginx.conf
COPY shaanxi-mobile-cdn.m3u \
     shaanxi-mobile-cdn-catchup.m3u \
     shaanxi-mobile-cdn-catchup-kodi.m3u \
     shaanxi-mobile-xian-gitv.m3u \
     shaanxi-mobile-cdn-diyp.txt \
     shaanxi-mobile-cdn-diyp-grouped.txt \
     shaanxi-mobile-xian-gitv-diyp.txt \
     shaanxi-mobile-xian-gitv-diyp-grouped.txt \
     /srv/iptv/
