#!/bin/sh
# Railway volumes mount root-owned regardless of image ownership, so the
# container starts as root, fixes /data ownership, and immediately drops
# privileges to the app user. Every other execution path runs unprivileged.
set -e
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data
    chown -R app:app /data
    exec runuser -u app -- "$@"
fi
exec "$@"
