#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

if [ -d "Partisan-Telegram-Android" ]; then
  cd Partisan-Telegram-Android
  git pull || exit 1
else
  git clone -b masking https://github.com/wrwrabbit/Partisan-Telegram-Android.git || exit 1
  cd Partisan-Telegram-Android
fi

cd ..

cp -R Partisan-Telegram-Android "$1/Partisan-Telegram-Android"
