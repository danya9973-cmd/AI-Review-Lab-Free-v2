#!/bin/zsh
set -euo pipefail

CONFIG_DIR="$HOME/Library/Application Support/AI Review Lab"
CONFIG_FILE="$CONFIG_DIR/.env"
mkdir -p "$CONFIG_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
  PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
  if [[ -f "$PROJECT_DIR/.env" ]]; then
    install -m 600 "$PROJECT_DIR/.env" "$CONFIG_FILE"
  else
    install -m 600 "$PROJECT_DIR/.env.example" "$CONFIG_FILE"
  fi
fi

open -e "$CONFIG_FILE"
