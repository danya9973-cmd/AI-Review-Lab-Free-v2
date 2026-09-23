"""Four-call council workflow: three independent analyses plus one synthesis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Any

from providers import BaseProvider, ProviderError


ANALYSIS_PROMPT = """다음 질문을 다른 AI의 답을 보지 않고 독립적으로 분석하세요.

<사용자 질문>
{question}
</사용자 질문>

반드시 다음을 포함하세요:
1. 핵심 결론
2. 확인된 사실과 추론의 구분
3. 실행 가능한 해결 방법
4. 위험, 예외, 추가 확인사항
모르는 내용은 단정하지 말고 '확인 필요'라고 표시하세요."""

SYNTHESIS_PROMPT = """세 개의 독립 분석을 검토해 사용자에게 줄 최종 답변을 작성하세요.
다수결로 결론 내리지 말고, 근거의 강도와 실행 가능성을 비교하세요. 의견이 다르면 차이를 명시하고 불확실성은 '확인 필요'로 표시하세요.

<사용자 질문>
{question}
</사용자 질문>

{analyses}

형식:
[결론]
[근거와 의견 차이]
[권장 실행 순서]
[주의사항 및 확인 필요]"""


def expected_calls(providers: dict[str, BaseProvider]) -> int:
    ready = sum(1 for provider in providers.values() if provider.ready)
    final_name = os.getenv("FINAL_PROVIDER", "gemini").strip().lower()
    return ready + (1 if ready and final_name in providers and providers[final_name].ready else 0)


def run_council(question: str, providers: dict[str, BaseProvider]) -> dict[str, Any]:
    ready = {name: provider for name, provider in providers.items() if provider.ready}
    if len(ready) != 3:
        missing = [provider.label for provider in providers.values() if not provider.ready]
        raise ProviderError(
            "council",
            "기본 4회 흐름을 실행하려면 세 공급자가 모두 준비되어야 합니다.",
            error_type="providers_not_ready",
            hint="준비되지 않은 공급자: " + ", ".join(missing),
        )

    results: dict[str, str] = {}
    errors: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(provider.generate, ANALYSIS_PROMPT.format(question=question)): name
            for name, provider in ready.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except ProviderError as exc:
                errors[name] = exc.to_dict()
            except Exception as exc:  # Defensive boundary; no secrets are serialized.
                errors[name] = ProviderError(name, str(exc), error_type="unexpected_error").to_dict()

    if errors:
        return {"ok": False, "analyses": results, "errors": errors, "calls_completed": len(results) + len(errors)}

    final_name = os.getenv("FINAL_PROVIDER", "gemini").strip().lower()
    final_provider = providers.get(final_name)
    if not final_provider or not final_provider.ready:
        raise ProviderError("council", "FINAL_PROVIDER가 준비된 공급자가 아닙니다.", error_type="invalid_final_provider")

    blocks = []
    for name in ("gemini", "groq", "openrouter"):
        blocks.append(f"<독립분석 provider=\"{name}\">\n{results[name]}\n</독립분석>")
    try:
        final = final_provider.generate(SYNTHESIS_PROMPT.format(question=question, analyses="\n\n".join(blocks)))
    except ProviderError as exc:
        return {
            "ok": False,
            "analyses": results,
            "errors": {"synthesis": exc.to_dict()},
            "calls_completed": 4,
            "final_provider": final_name,
        }
    return {
        "ok": True,
        "analyses": results,
        "final": final,
        "final_provider": final_name,
        "calls_completed": 4,
    }
