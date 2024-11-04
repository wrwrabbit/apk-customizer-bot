#!/bin/bash
set -e

# args: order_id, mock_error (unused), docker_image_name

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

cd Partisan-Telegram-Android
MOUNT_POINT="$1"
DOCKER_IMAGE_NAME="$2"
docker run -v "${MOUNT_POINT}":/home/source -m 10G "$DOCKER_IMAGE_NAME"
docker system prune -f
cd ..
touch "done"
