#!/bin/zsh
set -e
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo
  echo ".env 파일을 만들었습니다. API 키 3개를 입력한 뒤 이 파일을 다시 실행하세요."
  open -e .env
  exit 0
fi

open "http://127.0.0.1:5000"
exec .venv/bin/python app.py
