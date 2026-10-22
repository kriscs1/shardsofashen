#!/bin/sh
# Starts the server as the user PUID / PGID (default 1000; on Unraid 99 / 100, "nobody:users"), after making its data
# folder theirs, so the database can be written wherever /data is mapped (a Docker volume, or an appdata share).
set -e
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data
    chown -R "$PUID:$PGID" /data /game/Data
    exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
fi
exec "$@"
