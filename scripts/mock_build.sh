#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

if [ "$2" = "True" ]; then
    echo "[mock_build.sh] Mocking build failure"
    sleep 5
    exit 1
else
    echo "[mock_build.sh] Mocking successful build"
    APK_PATH="Partisan-Telegram-Android/TMessagesProj/build/outputs/apk/afat/release"
    mkdir -p ${APK_PATH}
    sleep 60
    echo "test" > ${APK_PATH}/app.apk
    touch "done"
fi