from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from council import expected_calls, run_council
from providers import ProviderError, build_providers


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=256 * 1024, JSON_AS_ASCII=False)
    if test_config:
        app.config.update(test_config)
    providers = build_providers()
    app.extensions["providers"] = providers

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        current = app.extensions["providers"]
        return jsonify(
            providers=[provider.public_status() for provider in current.values()],
            expected_calls=expected_calls(current),
            workflow="독립 분석 3회 + 최종 종합 1회",
            local_only=True,
        )

    @app.post("/api/test/<provider_name>")
    def test_provider(provider_name: str):
        current = app.extensions["providers"]
        provider = current.get(provider_name)
        if not provider:
            return jsonify(ok=False, error={"message": "알 수 없는 공급자입니다."}), 404
        started = time.monotonic()
        try:
            answer = provider.generate("연결 테스트입니다. '연결 성공'이라고만 답하세요.")
            return jsonify(ok=True, provider=provider_name, model=provider.config.model, latency_ms=round((time.monotonic() - started) * 1000), preview=answer[:120])
        except ProviderError as exc:
            return jsonify(ok=False, provider=provider_name, error=exc.to_dict()), 502

    @app.post("/api/review")
    def review():
        data = request.get_json(silent=True) or {}
        question = str(data.get("question", "")).strip()
        max_chars = int(os.getenv("MAX_QUESTION_CHARS", "12000"))
        if not question:
            return jsonify(ok=False, error={"message": "질문을 입력하세요."}), 400
        if len(question) > max_chars:
            return jsonify(ok=False, error={"message": f"질문은 {max_chars:,}자 이하로 입력하세요."}), 400
        try:
            result = run_council(question, app.extensions["providers"])
            return jsonify(result), 200 if result["ok"] else 502
        except ProviderError as exc:
            return jsonify(ok=False, error=exc.to_dict()), 400

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("보안을 위해 HOST는 127.0.0.1 또는 localhost만 허용됩니다.")
    app.run(host=host, port=int(os.getenv("PORT", "5000")), debug=os.getenv("DEBUG", "false").lower() == "true")
