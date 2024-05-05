#!/bin/bash
set -e

PTG_REVISION=9c71264196a22ad407db65a82b81fdd6155a6479

if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

if [ -d "Partisan-Telegram-Android" ]; then
    cd Partisan-Telegram-Android
    echo "[copy_repo.sh] Fetch PTG repository"
    git fetch origin master
else
    echo "[copy_repo.sh] Clone PTG repository"
    git clone https://github.com/wrwrabbit/Partisan-Telegram-Android.git
    cd Partisan-Telegram-Android
fi

cd ..
DST_PATH="$1/Partisan-Telegram-Android"
if [ -d ${DST_PATH}/.git ]; then
    cd ${DST_PATH}
    echo "[copy_repo.sh] Repo in $1 exists."
    echo "[copy_repo.sh] Resetting it to ${PTG_REVISION}"
    git reset --hard ${PTG_REVISION}
else
    rm -rf ${DST_PATH}
    echo "[copy_repo.sh] Clone PTG repo to $1"
    git clone -v Partisan-Telegram-Android ${DST_PATH}
    cd ${DST_PATH}
    echo "[copy_repo.sh] Checkout PTG revision ${PTG_REVISION}"
    git checkout ${PTG_REVISION}
fi
