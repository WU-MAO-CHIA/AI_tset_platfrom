"""Headless-Chromium page inspector driven by Playwright.

One instance = one exploration session (owns a browser + page).
Exposes small agent-friendly tools: goto / snapshot / screenshot /
click / fill / get_locators / close.

Element refs (e0, e1, ...) are stable within the latest snapshot; click /
fill / get_locators resolve refs through that snapshot's XPath cache.
"""

import ipaddress
import os
import socket
from typing import Any, Optional
from urllib.parse import urlparse


# JS: collect visible interactable elements with role/name + locator candidates.
_COLLECT_JS = """() => {
  const out = [];
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const st = window.getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') return false;
    return true;
  };
  const accName = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria && aria.trim()) return aria.trim().slice(0, 80);
    const id = el.getAttribute('id');
    if (id) {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab && lab.innerText.trim()) return lab.innerText.trim().slice(0, 80);
    }
    const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
    if (t) return t.slice(0, 80);
    for (const a of ['placeholder', 'title', 'alt', 'value', 'name']) {
      const v = el.getAttribute(a);
      if (v && v.trim()) return v.trim().slice(0, 80);
    }
    return '';
  };
  const implicitRole = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'a' && el.hasAttribute('href')) return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (['button', 'submit', 'reset'].includes(t)) return 'button';
      return 'textbox';
    }
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'img') return 'img';
    return '';
  };
  const segFor = (el) => {
    const id = el.getAttribute && el.getAttribute('id');
    if (id) return `//${el.tagName.toLowerCase()}[@id="${id}"]`;
    const dt = el.getAttribute && el.getAttribute('data-testid');
    if (dt) return `//${el.tagName.toLowerCase()}[@data-testid="${dt}"]`;
    return null;
  };
  const relXPath = (el) => {
    const anchored = segFor(el);
    if (anchored) return anchored;
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && cur.tagName.toLowerCase() !== 'html') {
      // stop early at an id/testid-anchored ancestor
      const anc = segFor(cur);
      if (anc && cur !== el) { parts.unshift(anc.replace(/^\\/\\//, '')); break; }
      let idx = 1, sib = cur.previousElementSibling;
      while (sib) {
        if (sib.tagName === cur.tagName) idx++;
        sib = sib.previousElementSibling;
      }
      parts.unshift(`${cur.tagName.toLowerCase()}[${idx}]`);
      cur = cur.parentElement;
      if (parts.length > 12) break;
    }
    return '//' + parts.join('/');
  };
  const cssFor = (el) => {
    const id = el.getAttribute && el.getAttribute('id');
    if (id) return `#${CSS.escape(id)}`;
    const dt = el.getAttribute && el.getAttribute('data-testid');
    if (dt) return `[data-testid="${dt}"]`;
    let path = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && cur.tagName.toLowerCase() !== 'body' && path.length < 4) {
      let s = cur.tagName.toLowerCase();
      const cls = (cur.getAttribute('class') || '').trim().split(/\\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) s += '.' + cls.map((c) => CSS.escape(c)).join('.');
      path.unshift(s);
      cur = cur.parentElement;
    }
    return path.join(' > ');
  };
  const recommended = (role, name, el) => {
    // 遵循專案 RF 規範：role=<role>[name="<name>"] > text= > id= / data-testid= > CSS
    const q = (s) => (s || '').replace(/"/g, '');
    if (role && name) return `role=${role}[name="${q(name)}"]`;
    const id = el.getAttribute && el.getAttribute('id');
    if (id) return `id=${id}`;
    const dt = el.getAttribute && el.getAttribute('data-testid');
    if (dt) return `data-testid=${dt}`;
    if (name) return `text=${q(name)}`;
    return `css=${cssFor(el)}`;
  };
  const SEL = 'a[href], button, input, select, textarea, [role="button"], [role="link"],'
    + ' [role="textbox"], [role="checkbox"], [role="radio"], [role="combobox"],'
    + ' [onclick], [data-testid]';
  for (const el of document.querySelectorAll(SEL)) {
    if (!isVisible(el)) continue;
    const role = el.getAttribute('role') || implicitRole(el);
    const name = accName(el);
    const xpath = relXPath(el);
    let unique = false;
    try {
      const r = document.evaluate(`count(${xpath})`, document, null,
        XPathResult.NUMBER_TYPE, null);
      unique = r.numberValue === 1;
    } catch (e) { unique = false; }
    out.push({
      tag: el.tagName.toLowerCase(),
      role, name,
      recommended: recommended(role, name, el),
      xpath, css: cssFor(el),
      xpath_unique: unique,
    });
    if (out.length >= 120) break;
  }
  return out;
}"""


def validate_explore_url(url: str) -> str:
    """Allow only http/https URLs whose host does not resolve to non-public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("只支援 http/https 網址")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError:
        raise ValueError("網址無法解析")
    ips = {info[4][0] for info in infos}
    for ip in ips:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
            or not addr.is_global
        ):
            raise ValueError("不允許探索內網 / 本機位址")
    return url


class PageExplorerService:
    """Owns one headless Chromium page for an exploration session."""

    def __init__(
        self,
        screenshot_dir: Optional[str] = None,
        viewport: Optional[dict] = None,
        goto_timeout_ms: int = 30000,
        action_timeout_ms: int = 10000,
    ) -> None:
        self.screenshot_dir = screenshot_dir
        self.viewport = viewport or {"width": 1280, "height": 800}
        self.goto_timeout_ms = goto_timeout_ms
        self.action_timeout_ms = action_timeout_ms
        self._pw = None
        self._browser = None
        self._page = None
        self._snapshot: list[dict] = []

    async def start(self) -> None:
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        context = await self._browser.new_context(viewport=self.viewport)
        self._page = await context.new_page()
        self._page.set_default_timeout(self.action_timeout_ms)

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()
            self._pw = None
            self._browser = None
            self._page = None
            self._snapshot = []

    def _require_page(self):
        if not self._page:
            raise RuntimeError("explorer not started")
        return self._page

    def _resolve(self, ref: str) -> str:
        for el in self._snapshot:
            if el["ref"] == ref:
                return el["xpath"]
        raise ValueError(f"未知元素 ref: {ref}（請先呼叫 snapshot）")

    async def goto(self, url: str) -> dict:
        validate_explore_url(url)
        page = self._require_page()
        await page.goto(url, timeout=self.goto_timeout_ms, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass  # SPA 長輪詢時略過，仍可繼續探索
        return {"ok": True, "title": await page.title(), "url": page.url}

    async def snapshot(self, max_elements: int = 80) -> dict:
        page = self._require_page()
        raw: list[dict] = await page.evaluate(_COLLECT_JS)
        self._snapshot = [
            {**el, "ref": f"e{i}"} for i, el in enumerate(raw[:max_elements])
        ]
        return {
            "url": page.url,
            "title": await page.title(),
            "elements": self._snapshot,
            "truncated": len(raw) > max_elements,
            "total": len(raw),
        }

    async def screenshot(self, name: str = "step.png") -> dict:
        page = self._require_page()
        path = None
        if self.screenshot_dir:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            path = os.path.join(self.screenshot_dir, name)
            await page.screenshot(path=path, full_page=False)
        else:
            await page.screenshot(full_page=False)
        return {"ok": True, "path": path}

    async def click(self, ref: str) -> dict:
        page = self._require_page()
        xpath = self._resolve(ref)
        await page.locator(f"xpath={xpath}").first.click(timeout=self.action_timeout_ms)
        await page.wait_for_timeout(800)
        return {"ok": True, "ref": ref}

    async def fill(self, ref: str, value: str) -> dict:
        page = self._require_page()
        xpath = self._resolve(ref)
        await page.locator(f"xpath={xpath}").first.fill(value, timeout=self.action_timeout_ms)
        # NOTE: caller must mask `value` in any log/observation
        return {"ok": True, "ref": ref}

    async def get_locators(self, ref: str) -> dict:
        for el in self._snapshot:
            if el["ref"] == ref:
                return {
                    "ref": ref,
                    "role": el.get("role", ""),
                    "name": el.get("name", ""),
                    "recommended": el.get("recommended", ""),
                    "xpath": el.get("xpath", ""),
                    "css": el.get("css", ""),
                    "xpath_unique": el.get("xpath_unique", False),
                }
        raise ValueError(f"未知元素 ref: {ref}（請先呼叫 snapshot）")

    async def current_url(self) -> str:
        return self._require_page().url
