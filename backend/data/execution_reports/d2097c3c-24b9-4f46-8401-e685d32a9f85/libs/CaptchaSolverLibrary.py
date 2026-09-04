"""
CaptchaSolverLibrary — Robot Framework keyword library for solving image CAPTCHAs.

Uses the active LLM model from the backend admin settings (GET /api/v1/llm-models).
Falls back to claude-haiku-4-5-20251001 if backend is unreachable.

Supports Anthropic Claude (vision), OpenAI GPT-4o (vision), and Ollama (vision).

Usage in .robot file:
    Library    ${CURDIR}/../libs/CaptchaSolverLibrary.py

Keywords:
    Solve Captcha From File          ${image_path}
    Solve Captcha From Element       ${selector}
    Solve Captcha From Base64        ${base64_data}    ${media_type}
"""
import base64
import json
import os
import time
import urllib.request
from pathlib import Path


_FALLBACK_MODEL = "claude-haiku-4-5-20251001"

_DEFAULT_PROMPT = (
    "這是一張圖形驗證碼（CAPTCHA）。請仔細辨識圖中的所有字元（英文字母與數字）。"
    "只回傳驗證碼文字本身，不要包含任何說明、標點符號或空格。"
    "若無法辨識，回傳空字串。"
)


def _load_env(key: str) -> str:
    """Try to read a key from backend/.env if not already in os.environ."""
    val = os.environ.get(key, "")
    if val:
        return val
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _fetch_active_model(backend_url: str) -> str:
    """Query backend for the currently active LLM model. Returns empty string on failure."""
    try:
        url = f"{backend_url.rstrip('/')}/api/v1/llm-models"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("default", "")
    except Exception:
        return ""


def _provider(model_id: str) -> str:
    if model_id.startswith("ollama:"):
        return "ollama"
    if model_id.startswith("gpt-") or model_id.startswith("o1"):
        return "openai"
    return "anthropic"


def _call_anthropic(image_data: str, media_type: str, prompt: str, model: str, max_retries: int) -> str:
    import anthropic
    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment or backend/.env")
    client = anthropic.Anthropic(api_key=api_key)
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=64,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Anthropic CAPTCHA solving failed: {last_err}")


def _call_openai(image_data: str, media_type: str, prompt: str, model: str, max_retries: int) -> str:
    import openai  # type: ignore[import-untyped]
    api_key = _load_env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment or backend/.env")
    client = openai.OpenAI(api_key=api_key)
    data_url = f"data:{media_type};base64,{image_data}"
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=64,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"OpenAI CAPTCHA solving failed: {last_err}")


def _call_ollama(image_data: str, media_type: str, prompt: str, model: str, max_retries: int) -> str:
    _ = media_type  # reserved for future multimodal Ollama support
    ollama_base = _load_env("OLLAMA_BASE_URL") or "http://localhost:11434"
    model_name = model.removeprefix("ollama:")
    url = f"{ollama_base.rstrip('/')}/api/generate"
    payload = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "images": [image_data],
        "stream": False,
    }).encode()
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip()
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Ollama CAPTCHA solving failed: {last_err}")


class CaptchaSolverLibrary:
    """Robot Framework library for CAPTCHA image recognition via the active LLM model."""

    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        model: str = "",
        max_retries: int = 2,
    ):
        self._backend_url = backend_url
        self._override_model = model  # if set, skip backend query
        self._max_retries = max_retries

    def _resolve_model(self) -> str:
        if self._override_model:
            return self._override_model
        active = _fetch_active_model(self._backend_url)
        if active:
            return active
        return _FALLBACK_MODEL

    def solve_captcha_from_file(self, image_path: str, prompt: str = _DEFAULT_PROMPT) -> str:
        """Read a CAPTCHA image from *image_path* and return the recognised text.

        Example:
        | ${text}= | Solve Captcha From File | /tmp/captcha.png |
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"CAPTCHA image not found: {image_path}")
        ext = path.suffix.lower().lstrip(".")
        media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                      "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
        image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        return self._dispatch(image_data, media_type, prompt)

    def solve_captcha_from_base64(
        self, base64_data: str, media_type: str = "image/png", prompt: str = _DEFAULT_PROMPT
    ) -> str:
        """Solve CAPTCHA from a base64-encoded image string.

        Example:
        | ${text}= | Solve Captcha From Base64 | ${b64} | image/png |
        """
        return self._dispatch(base64_data, media_type, prompt)

    def solve_captcha_from_element(
        self, selector: str, output_file: str = "", prompt: str = _DEFAULT_PROMPT
    ) -> str:
        """Take a screenshot of *selector* using the active Browser page and solve the CAPTCHA.

        Example:
        | ${text}= | Solve Captcha From Element | id=imgCaptcha |
        """
        from robot.libraries.BuiltIn import BuiltIn
        built_in = BuiltIn()
        browser = built_in.get_library_instance("Browser")
        if not output_file:
            import tempfile
            output_file = os.path.join(tempfile.gettempdir(), f"captcha_{int(time.time()*1000)}.png")
        browser.take_screenshot(filename=output_file, selector=selector, fullPage=False)
        return self.solve_captcha_from_file(output_file, prompt)

    def _dispatch(self, image_data: str, media_type: str, prompt: str) -> str:
        model = self._resolve_model()
        provider = _provider(model)
        if provider == "openai":
            return _call_openai(image_data, media_type, prompt, model, self._max_retries)
        if provider == "ollama":
            return _call_ollama(image_data, media_type, prompt, model, self._max_retries)
        return _call_anthropic(image_data, media_type, prompt, model, self._max_retries)
