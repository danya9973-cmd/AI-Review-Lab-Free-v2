"""Configuration and opt-in live connection diagnostics."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import load_dotenv

from providers import ProviderError, build_providers


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Review Lab 공급자 진단")
    parser.add_argument("--live", action="store_true", help="각 준비된 공급자에 실제로 1회 요청합니다.")
    parser.add_argument("--provider", choices=["all", "gemini", "groq", "openrouter"], default="all")
    parser.add_argument("--output", help="JSON 결과 저장 경로")
    args = parser.parse_args()
    load_dotenv()
    providers = build_providers()
    selected = providers.values() if args.provider == "all" else [providers[args.provider]]
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if args.live else "offline",
        "providers": [],
    }
    for provider in selected:
        item = provider.public_status()
        if args.live and provider.ready:
            try:
                item.update(test_ok=True, response_preview=provider.generate("연결 테스트입니다. '연결 성공'이라고만 답하세요.")[:120])
            except ProviderError as exc:
                item.update(test_ok=False, error=exc.to_dict())
        elif args.live:
            item.update(test_ok=False, error={"message": "비활성화되었거나 API 키가 없습니다."})
        report["providers"].append(item)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    failed = any(item.get("test_ok") is False for item in report["providers"])
    return 1 if args.live and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
