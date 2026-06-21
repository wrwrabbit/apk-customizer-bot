#!/bin/bash
set -e

# args: mount_point, docker_image_name

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

cd Partisan-Telegram-Android
MOUNT_POINT="$1"
DOCKER_IMAGE_NAME="$2"
docker build -f Dockerfile -t "$DOCKER_IMAGE_NAME" .
docker run -v "${MOUNT_POINT}":/home/source -m 10G --rm "$DOCKER_IMAGE_NAME"
docker rmi -f "$DOCKER_IMAGE_NAME" || true
docker system prune -f
cd ..
touch "done"
