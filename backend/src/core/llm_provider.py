import logging
from typing import Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)

# 5 分鐘 TTL：對話與探索 agent 的連續請求多在 5 分鐘內，讀取會刷新計時，比 1 小時 TTL（寫入 2 倍）便宜
_EPHEMERAL_CACHE = {"type": "ephemeral"}


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, prompt: str) -> str:
        ...

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        ...

    async def complete_with_messages(self, messages: list[dict], system: str = "", cache_prefix: str = "") -> str:
        """cache_prefix：system 開頭固定不變的部分（須為 system 的前綴），支援 prompt caching 的
        provider 會在其結尾設快取點；空字串表示整段 system 都固定。"""
        ...


def _anthropic_system_blocks(system: str, cache_prefix: str) -> list[dict]:
    """在 system 固定開頭的結尾設快取點；其後每次可能不同的內容（RF 程式碼、頁面元素）放在快取點之後，
    變動時不會讓固定開頭的快取失效。"""
    if cache_prefix and not system.startswith(cache_prefix):
        # 呼叫端給的前綴對不上：不設快取點，避免每次都付寫入費卻讀不到
        return [{"type": "text", "text": system}]
    stable = cache_prefix or system
    blocks = [{"type": "text", "text": stable, "cache_control": _EPHEMERAL_CACHE}]
    rest = system[len(stable):]
    if rest.strip():
        blocks.append({"type": "text", "text": rest})
    return blocks


class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022") -> None:
        self.model = model
        self._api_key = api_key

    def _get_client(self):
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=self._api_key)

    async def complete(self, prompt: str) -> str:
        client = self._get_client()
        message = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        import base64
        import aiofiles

        client = self._get_client()
        content: list = []

        for media in media_list:
            if getattr(media, "attachment_type", None) == "image" and media.file_path:
                try:
                    async with aiofiles.open(media.file_path, "rb") as f:
                        data = await f.read()
                    b64 = base64.standard_b64encode(data).decode()
                    mime = getattr(media, "mime_type", None) or "image/png"
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime, "data": b64},
                    })
                except OSError:
                    pass  # Skip missing files

        content.append({"type": "text", "text": prompt})

        message = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text

    async def complete_with_messages(self, messages: list[dict], system: str = "", cache_prefix: str = "") -> str:
        client = self._get_client()
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": messages,
            # 自動快取：快取點跟著對話尾端前進，每輪都能讀到前面已快取的歷史
            "cache_control": _EPHEMERAL_CACHE,
        }
        if system:
            kwargs["system"] = _anthropic_system_blocks(system, cache_prefix)
        message = await client.messages.create(**kwargs)
        usage = message.usage
        # 低於模型的最低可快取長度時 API 不報錯、只是不快取，靠這行確認實際命中情形
        logger.info(
            "anthropic %s tokens: input=%s cache_write=%s cache_read=%s output=%s",
            self.model, usage.input_tokens, usage.cache_creation_input_tokens or 0,
            usage.cache_read_input_tokens or 0, usage.output_tokens,
        )
        return message.content[0].text


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.model = model
        self._api_key = api_key

    def _get_client(self):
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=self._api_key)

    async def complete(self, prompt: str) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        import base64
        import aiofiles

        client = self._get_client()
        content: list = []

        for media in media_list:
            if getattr(media, "attachment_type", None) == "image" and media.file_path:
                try:
                    async with aiofiles.open(media.file_path, "rb") as f:
                        data = await f.read()
                    b64 = base64.standard_b64encode(data).decode()
                    mime = getattr(media, "mime_type", None) or "image/png"
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    })
                except OSError:
                    pass

        content.append({"type": "text", "text": prompt})

        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    async def complete_with_messages(self, messages: list[dict], system: str = "", cache_prefix: str = "") -> str:
        client = self._get_client()
        all_messages = messages
        if system:
            all_messages = [{"role": "system", "content": system}] + messages
        response = await client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""


class OllamaProvider:
    """本地 Ollama 原生 API（POST /api/chat，stream:false）。

    模型名去除 `ollama:` 前綴後送出；vision 退化為純文字（本地模型多無視覺能力）。
    """

    def __init__(self, base_url: str, model: str = "llama3", timeout: float = 120.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        # 去除 ollama: 前綴，Ollama 端只認得裸模型名
        self.model = model[len("ollama:"):] if model.startswith("ollama:") else model
        self._timeout = timeout

    async def _chat(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
        return (data.get("message") or {}).get("content", "")

    async def complete(self, prompt: str) -> str:
        return await self._chat([{"role": "user", "content": prompt}])

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        # 本地模型多不支援視覺；退化為純文字
        return await self.complete(prompt)

    async def complete_with_messages(self, messages: list[dict], system: str = "", cache_prefix: str = "") -> str:
        all_messages = messages
        if system:
            all_messages = [{"role": "system", "content": system}] + messages
        return await self._chat(all_messages)


def get_provider(model_id: str, settings) -> LLMProvider:
    if model_id.startswith("ollama:"):
        return OllamaProvider(base_url=settings.ollama_base_url, model=model_id)
    if model_id.startswith("claude"):
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=model_id)
    return OpenAIProvider(api_key=settings.openai_api_key, model=model_id)
