#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "이 빌드는 macOS에서만 실행할 수 있습니다."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo ".env 파일이 없습니다. .env.example을 복사하고 API 키를 설정하세요."
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

CONFIG_DIR="$HOME/Library/Application Support/AI Review Lab"
if [[ "${SKIP_CONFIG_COPY:-0}" != "1" ]]; then
  mkdir -p "$CONFIG_DIR"
  install -m 600 .env "$CONFIG_DIR/.env"
fi

export PYINSTALLER_CONFIG_DIR="$PROJECT_DIR/.pyinstaller"

.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "AIReviewLab" \
  --osx-bundle-identifier "com.digeum.aireviewlab" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  desktop.py

echo
echo "빌드 완료: $PROJECT_DIR/dist/AIReviewLab.app"
echo "API 설정: $CONFIG_DIR/.env"
open -R "$PROJECT_DIR/dist/AIReviewLab.app" || true
