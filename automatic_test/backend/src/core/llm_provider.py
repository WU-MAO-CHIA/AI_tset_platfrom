from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, prompt: str) -> str:
        ...

    async def complete_with_vision(self, prompt: str, media_list: list) -> str:
        ...

    async def complete_with_messages(self, messages: list[dict], system: str = "") -> str:
        ...


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

    async def complete_with_messages(self, messages: list[dict], system: str = "") -> str:
        client = self._get_client()
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        message = await client.messages.create(**kwargs)
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

    async def complete_with_messages(self, messages: list[dict], system: str = "") -> str:
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


def get_provider(model_id: str, settings) -> LLMProvider:
    if model_id.startswith("claude"):
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=model_id)
    return OpenAIProvider(api_key=settings.openai_api_key, model=model_id)
