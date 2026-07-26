#!/bin/sh
set -e

dockerd &

timeout=30
until docker info >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ "$timeout" -le 0 ]; then
        echo "dockerd did not become ready in time" >&2
        exit 1
    fi
    sleep 1
done

exec python -u -m worker.build_worker
