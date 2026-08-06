from __future__ import annotations

import httpx
import pytest

from pinesprout.generators.ai_generator import (
    GenerationError,
    GenerationRequest,
    _extract_code_block,
    generate_pine_script,
)


def test_extract_code_block_with_fence():
    text = 'Here is your script:\n```pine\n//@version=6\nindicator("x")\n```\nEnjoy!'
    code = _extract_code_block(text)
    assert code.startswith("//@version=6")
    assert "```" not in code


def test_extract_code_block_without_fence_falls_back():
    text = '//@version=6\nindicator("x")\n'
    code = _extract_code_block(text)
    assert "indicator" in code


def test_generate_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    request = GenerationRequest(prompt="a simple sma indicator")
    with pytest.raises(GenerationError, match="API key"):
        generate_pine_script(request, api_key=None)


def test_generate_success_with_mocked_transport(monkeypatch):
    request = GenerationRequest(prompt="a simple sma indicator")

    fake_response_body = {
        "content": [
            {"type": "text", "text": '```pine\n//@version=6\nindicator("SMA")\nplot(ta.sma(close, 14))\n```'}
        ]
    }

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fake_response_body)

    transport = httpx.MockTransport(handler)
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("pinesprout.generators.ai_generator.httpx.Client", fake_client)

    result = generate_pine_script(request, api_key="fake-key")
    assert "indicator" in result.source
    assert result.detected_version == 6
    assert isinstance(result.lint_issues, list)


def test_generate_raises_on_http_error(monkeypatch):
    request = GenerationRequest(prompt="a simple sma indicator")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    transport = httpx.MockTransport(handler)
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("pinesprout.generators.ai_generator.httpx.Client", fake_client)

    with pytest.raises(GenerationError):
        generate_pine_script(request, api_key="fake-key")
