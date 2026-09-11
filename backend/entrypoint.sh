#!/bin/sh
# Dispatches the three process kinds of the platform from one image.
set -eu
cmd="${1:-api}"
[ "$#" -gt 0 ] && shift
case "$cmd" in
  api)
    exec granian --interface asgi --host 0.0.0.0 --port "${PORT:-8080}" \
      --workers "${WEB_CONCURRENCY:-1}" mizan.config.asgi:application "$@" ;;
  worker)
    exec python manage.py procrastinate worker --concurrency "${WORKER_CONCURRENCY:-4}" "$@" ;;
  scheduler)
    exec python manage.py scheduler_tick "$@" ;;
  migrate)
    exec python manage.py migrate --noinput "$@" ;;
  *)
    exec "$cmd" "$@" ;;
esac
