"""Unit tests for CaptchaSolverLibrary (FR-028).

Tests cover:
- Provider routing by model ID prefix
- Active model resolution (override / backend / fallback)
- File-not-found error handling
- _fetch_active_model graceful failure
"""

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Import module-level helpers without importing the full class
# (avoids needing robot/anthropic installed at test time)
from libs.CaptchaSolverLibrary import (
    _FALLBACK_MODEL,
    CaptchaSolverLibrary,
    _fetch_active_model,
    _provider,
)


class TestProviderRouting:
    def test_claude_model_routes_to_anthropic(self):
        assert _provider("claude-haiku-4-5-20251001") == "anthropic"

    def test_claude_sonnet_routes_to_anthropic(self):
        assert _provider("claude-sonnet-4-6") == "anthropic"

    def test_gpt4o_routes_to_openai(self):
        assert _provider("gpt-4o") == "openai"

    def test_gpt4o_mini_routes_to_openai(self):
        assert _provider("gpt-4o-mini") == "openai"

    def test_o1_routes_to_openai(self):
        assert _provider("o1-preview") == "openai"

    def test_ollama_prefix_routes_to_ollama(self):
        assert _provider("ollama:gemma4:e4b") == "ollama"

    def test_unknown_model_defaults_to_anthropic(self):
        assert _provider("some-unknown-model") == "anthropic"


class TestFetchActiveModel:
    def test_returns_empty_string_on_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = _fetch_active_model("http://localhost:9999")
        assert result == ""

    def test_returns_empty_string_on_invalid_json(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not-json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_active_model("http://localhost:8000")
        assert result == ""

    def test_returns_default_field_from_response(self):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"models": [], "default": "gpt-4o"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_active_model("http://localhost:8000")
        assert result == "gpt-4o"

    def test_returns_empty_when_default_key_missing(self):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"models": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_active_model("http://localhost:8000")
        assert result == ""


class TestResolveModel:
    def test_override_model_skips_backend_query(self):
        lib = CaptchaSolverLibrary(backend_url="http://localhost:8000", model="gpt-4o")
        with patch("libs.CaptchaSolverLibrary._fetch_active_model") as mock_fetch:
            result = lib._resolve_model()
        mock_fetch.assert_not_called()
        assert result == "gpt-4o"

    def test_uses_backend_model_when_no_override(self):
        lib = CaptchaSolverLibrary(backend_url="http://localhost:8000", model="")
        with patch("libs.CaptchaSolverLibrary._fetch_active_model", return_value="claude-sonnet-4-6"):
            result = lib._resolve_model()
        assert result == "claude-sonnet-4-6"

    def test_fallback_when_backend_unreachable(self):
        lib = CaptchaSolverLibrary(backend_url="http://localhost:9999", model="")
        with patch("libs.CaptchaSolverLibrary._fetch_active_model", return_value=""):
            result = lib._resolve_model()
        assert result == _FALLBACK_MODEL

    def test_fallback_model_is_claude_haiku(self):
        assert _FALLBACK_MODEL == "claude-haiku-4-5-20251001"


class TestSolveCaptchaFromFile:
    def test_raises_file_not_found_for_missing_file(self):
        lib = CaptchaSolverLibrary()
        with pytest.raises(FileNotFoundError, match="CAPTCHA image not found"):
            lib.solve_captcha_from_file("/nonexistent/path/captcha.png")

    def test_reads_file_and_dispatches(self):
        lib = CaptchaSolverLibrary(model="claude-haiku-4-5-20251001")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            tmp_path = f.name
        try:
            with patch.object(lib, "_dispatch", return_value="AB12") as mock_dispatch:
                result = lib.solve_captcha_from_file(tmp_path)
            mock_dispatch.assert_called_once()
            assert result == "AB12"
        finally:
            os.unlink(tmp_path)
