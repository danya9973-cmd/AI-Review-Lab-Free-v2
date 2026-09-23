import json
import os
import unittest
from unittest.mock import patch

from app import create_app
from council import run_council
from providers import GeminiProvider, GroqProvider, OpenRouterProvider, ProviderError


class FakeResponse:
    def __init__(self, payload, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.text = json.dumps(payload, ensure_ascii=False)
        self.ok = 200 <= status < 300

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class StubProvider:
    def __init__(self, name):
        self.name = name
        self.label = name.title()
        self.ready = True
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"{self.name} answer {len(self.prompts)}"


class OfflineTests(unittest.TestCase):
    def test_gemini_parses_text_and_keeps_key_out_of_json_headers(self):
        session = FakeSession([FakeResponse({"candidates": [{"content": {"parts": [{"text": "성공"}]}}]})])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret", "ENABLE_GEMINI": "true"}, clear=False):
            provider = GeminiProvider(session)
            self.assertEqual(provider.generate("test"), "성공")
            _, kwargs = session.calls[0]
            self.assertNotIn("secret", json.dumps(kwargs["json"]))
            self.assertNotIn("secret", session.calls[0][0])

    def test_openai_compatible_providers_parse_text(self):
        payload = {"choices": [{"message": {"content": "성공"}}]}
        for cls, key in [(GroqProvider, "GROQ_API_KEY"), (OpenRouterProvider, "OPENROUTER_API_KEY")]:
            with self.subTest(cls=cls.__name__), patch.dict(os.environ, {key: "secret"}, clear=False):
                self.assertEqual(cls(FakeSession([FakeResponse(payload)])).generate("test"), "성공")

    def test_provider_error_exposes_details_not_authorization_header(self):
        session = FakeSession([FakeResponse({"error": {"message": "rate limited: do-not-leak", "type": "rate_limit"}}, 429, {"x-request-id": "req-1"})])
        with patch.dict(os.environ, {"GROQ_API_KEY": "do-not-leak"}, clear=False):
            with self.assertRaises(ProviderError) as caught:
                GroqProvider(session).generate("test")
        detail = caught.exception.to_dict()
        self.assertEqual(detail["status_code"], 429)
        self.assertNotIn("do-not-leak", json.dumps(detail))

    def test_council_is_exactly_four_calls(self):
        providers = {name: StubProvider(name) for name in ("gemini", "groq", "openrouter")}
        with patch.dict(os.environ, {"FINAL_PROVIDER": "gemini"}, clear=False):
            result = run_council("질문", providers)
        self.assertTrue(result["ok"])
        self.assertEqual(result["calls_completed"], 4)
        self.assertEqual(sum(len(provider.prompts) for provider in providers.values()), 4)

    def test_status_never_returns_keys(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "hidden-key"}, clear=False):
            app = create_app({"TESTING": True})
            response = app.test_client().get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hidden-key", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
