#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

if [ -d "Partisan-Telegram-Android" ]; then
  cd Partisan-Telegram-Android
  old_commit_count=$(git rev-list --count HEAD)
  git pull || exit 1
  new_commit_count=$(git rev-list --count HEAD)
  if [ "$old_commit_count" -ne "$new_commit_count" ]; then
    need_rebuild=true
  else
    need_rebuild=false
  fi
else
  git clone -b masking https://github.com/wrwrabbit/Partisan-Telegram-Android.git || exit 1
  cd Partisan-Telegram-Android
  need_rebuild=true
fi

if [ $need_rebuild = true ]; then
  docker build -f Dockerfile -t "$2" .  || exit 1
  docker system prune -f
fi

cd ..

cp -R Partisan-Telegram-Android "$1/Partisan-Telegram-Android"
