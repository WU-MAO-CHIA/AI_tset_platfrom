"""Unit tests for PageAgentService and explore helpers.

No real browser or LLM is used: the provider is scripted and the explorer
is faked. Network-dependent checks use localhost (no external access).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.page_agent_service import PageAgentService
from src.services.page_explorer_service import validate_explore_url


def _tool(action: str, **kwargs) -> str:
    import json
    payload = {"action": action, **kwargs}
    return f"先看一下頁面\n```tool\n{json.dumps(payload, ensure_ascii=False)}\n```"


class FakeExplorer:
    """Minimal PageExplorerService double with canned snapshot."""

    def __init__(self):
        self.started = False
        self.closed = False
        self.fills: list[tuple] = []
        self._snapshot = [
            {"ref": "e0", "role": "textbox", "name": "帳號",
             "recommended": "role=textbox[name=\"帳號\"]",
             "xpath": "//input[@id=\"acc\"]", "css": "#acc", "xpath_unique": True},
            {"ref": "e1", "role": "button", "name": "登入",
             "recommended": "role=button[name=\"登入\"]",
             "xpath": "//button[1]", "css": "button", "xpath_unique": True},
        ]

    async def start(self):
        self.started = True

    async def close(self):
        self.closed = True

    async def goto(self, url):
        return {"ok": True, "title": "t", "url": url}

    async def snapshot(self, max_elements=80):
        return {"url": "http://x/", "title": "t", "elements": self._snapshot,
                "truncated": False, "total": len(self._snapshot)}

    async def click(self, ref):
        return {"ok": True, "ref": ref}

    async def fill(self, ref, value):
        self.fills.append((ref, value))
        return {"ok": True, "ref": ref}

    async def get_locators(self, ref):
        for el in self._snapshot:
            if el["ref"] == ref:
                return dict(el)
        raise ValueError(f"未知元素 ref: {ref}")


def _provider_scripted(responses: list[str]):
    provider = MagicMock()
    provider.complete_with_messages = AsyncMock(side_effect=list(responses))
    return provider


class TestParseToolCall:
    def test_parses_valid_block(self):
        call = PageAgentService.parse_tool_call(_tool("snapshot"))
        assert call == {"action": "snapshot"}

    def test_returns_none_without_block(self):
        assert PageAgentService.parse_tool_call("純文字，沒有工具") is None

    def test_returns_none_for_bad_json(self):
        assert PageAgentService.parse_tool_call("```tool\n{not json}\n```") is None


class TestMaskSecrets:
    def test_masks_values(self):
        out = PageAgentService.mask_secrets("填入 9907mkmnK 完成", ["9907mkmnK", "markwu"])
        assert "9907mkmnK" not in out
        assert "***" in out

    def test_short_values_ignored(self):
        assert PageAgentService.mask_secrets("a b", ["a"]) == "a b"


class TestExploreLoop:
    async def test_snapshot_then_finish_builds_catalog(self):
        provider = _provider_scripted([
            _tool("snapshot"),
            _tool("get_locators", ref="e1"),
            _tool("finish", findings=[
                {"goal": "登入按鈕", "ref": "e1", "status": "found", "note": ""},
                {"goal": "不存在的東西", "ref": "", "status": "not_found", "note": "沒看到"},
            ]),
        ])
        explorer = FakeExplorer()
        agent = PageAgentService(provider=provider, explorer_factory=lambda: explorer)
        result = await agent.explore("http://example.com/", ["登入按鈕", "不存在的東西"])

        assert result["status"] == "done"
        assert result["steps_used"] == 3
        by_goal = {c["goal"]: c for c in result["catalog"]}
        assert by_goal["登入按鈕"]["xpath"] == "//button[1]"
        assert by_goal["登入按鈕"]["recommended"] == 'role=button[name="登入"]'
        assert by_goal["不存在的東西"]["status"] == "not_found"
        assert explorer.closed is True

    async def test_fill_uses_server_side_value_and_masks_it(self):
        secret = "s3cr3t-pw"
        provider = _provider_scripted([
            _tool("fill", ref="e0", variable="${PASSWORD}"),
            _tool("finish", findings=[{"goal": "帳號", "ref": "e0", "status": "found", "note": ""}]),
        ])
        explorer = FakeExplorer()
        agent = PageAgentService(provider=provider, explorer_factory=lambda: explorer)
        await agent.explore("http://example.com/", ["帳號"], credentials={"PASSWORD": secret})

        # Real value reaches the browser tool…
        assert explorer.fills == [("e0", secret)]
        # …but never leaks into the next LLM prompt
        for call in provider.complete_with_messages.call_args_list[1:]:
            history = call.args[0]
            for msg in history:
                assert secret not in msg["content"]

    async def test_fill_is_case_insensitive_on_variable_name(self):
        """${username} must resolve the same as ${USERNAME}."""
        provider = _provider_scripted([
            _tool("fill", ref="e0", variable="${username}"),
            _tool("finish", findings=[{"goal": "帳號", "ref": "e0", "status": "found", "note": ""}]),
        ])
        explorer = FakeExplorer()
        agent = PageAgentService(provider=provider, explorer_factory=lambda: explorer)
        result = await agent.explore("http://example.com/", ["帳號"], credentials={"USERNAME": "markwu"})
        assert result["status"] == "done"
        assert explorer.fills == [("e0", "markwu")]

    async def test_fill_unknown_variable_reports_error(self):
        provider = _provider_scripted([
            _tool("fill", ref="e0", variable="${MISSING}"),
            _tool("finish", findings=[]),
        ])
        agent = PageAgentService(provider=provider, explorer_factory=FakeExplorer)
        result = await agent.explore("http://example.com/", ["帳號"], credentials={})
        assert result["status"] == "empty"
        # second LLM turn must have seen the missing-variable error
        second_history = provider.complete_with_messages.call_args_list[1].args[0]
        assert any("缺少登入變數" in m["content"] for m in second_history)

    async def test_goto_failure_returns_error(self):
        class BadExplorer(FakeExplorer):
            async def goto(self, url):
                raise RuntimeError("boom")

        provider = _provider_scripted([])
        agent = PageAgentService(provider=provider, explorer_factory=BadExplorer)
        result = await agent.explore("http://example.com/", ["x"])
        assert result["status"] == "error"
        assert "無法開啟網址" in result["note"]
        provider.complete_with_messages.assert_not_called()

    async def test_step_cap_returns_partial(self):
        provider = _provider_scripted([_tool("snapshot")] * 5)
        agent = PageAgentService(provider=provider, explorer_factory=FakeExplorer, max_steps=3)
        result = await agent.explore("http://example.com/", ["x"])
        assert result["status"] == "partial"
        assert result["steps_used"] == 3


class TestValidateExploreUrl:
    def test_rejects_non_http(self):
        with pytest.raises(ValueError):
            validate_explore_url("ftp://example.com/x")

    def test_rejects_unresolvable(self):
        with pytest.raises(ValueError):
            validate_explore_url("https://nonexistent.invalid-xyz-123/")

    def test_rejects_loopback_without_network(self):
        # localhost resolves locally — no external access needed
        with pytest.raises(ValueError, match="內網"):
            validate_explore_url("http://localhost:8000/api/v1/cases")


class TestResolveCredentialVars:
    def test_matches_rf_variable_and_field_name(self):
        from src.api.cases import _resolve_credential_vars

        rows = [
            MagicMock(rf_variable="${USERNAME}", field_name="使用者代碼", field_value="markwu"),
            MagicMock(rf_variable=None, field_name="ID", field_value="A123"),
            MagicMock(rf_variable="${PASSWORD}", field_name="密碼", field_value=""),
        ]
        creds = _resolve_credential_vars(rows, ["${USERNAME}", "ID", "${PASSWORD}", "${NOPE}"])
        assert creds == {"USERNAME": "markwu", "ID": "A123"}

    def test_empty_request_returns_empty(self):
        from src.api.cases import _resolve_credential_vars
        assert _resolve_credential_vars([], None) == {}
