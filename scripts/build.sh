#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

cd Partisan-Telegram-Android
docker build -t telegram-build .
MOUNT_POINT="${TMP_DIR_ABSPATH_ON_HOST}/$1/Partisan-Telegram-Android"
docker run --rm -v ${MOUNT_POINT}:/home/source -m 6000M telegram-build
cd ..
touch "done"
