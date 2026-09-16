#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Illegal number of parameters"
    exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/wrwrabbit/Partisan-Telegram-Android.git}"
REPO_BRANCH="${REPO_BRANCH:-masking}"

export GIT_TERMINAL_PROMPT=0

if [ -n "$GITHUB_TOKEN" ]; then
  export GIT_CONFIG_COUNT=2
  export GIT_CONFIG_KEY_0="credential.https://github.com.username"
  export GIT_CONFIG_VALUE_0="x-access-token"
  export GIT_CONFIG_KEY_1="credential.https://github.com.helper"
  export GIT_CONFIG_VALUE_1='!f() { echo "password=$GITHUB_TOKEN"; }; f'
fi

if [ -d "Partisan-Telegram-Android" ]; then
  if [ "$(git -C Partisan-Telegram-Android config --get remote.origin.url)" != "$REPO_URL" ]; then
    rm -rf Partisan-Telegram-Android
  fi
fi

if [ -d "Partisan-Telegram-Android" ]; then
  cd Partisan-Telegram-Android
  git fetch origin || exit 1
  git checkout "$REPO_BRANCH" || exit 1
  git pull || exit 1
  git submodule sync --recursive || exit 1
  git submodule update --init --recursive --depth=1 || exit 1
else
  git clone -b "$REPO_BRANCH" --recursive --shallow-submodules "$REPO_URL" Partisan-Telegram-Android || exit 1
  cd Partisan-Telegram-Android
fi

cd ..

cp -R Partisan-Telegram-Android "$1/Partisan-Telegram-Android"
