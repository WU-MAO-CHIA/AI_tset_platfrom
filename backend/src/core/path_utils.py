"""路徑安全共用函式：防止 path traversal / 絕對路徑覆寫。"""
from pathlib import Path


def safe_join(base_dir: str | Path, *parts: str) -> Path:
    """將 parts 接到 base_dir 下，回傳 resolve 後路徑；超出 base 即 raise ValueError。

    - 拒絕絕對路徑、空字串、含 NUL 的部分
    - 呼叫端應捕捉 ValueError 轉 404（避免洩露檔案是否存在以外的資訊）
    """
    base = Path(base_dir).resolve()
    cleaned: list[str] = []
    for p in parts:
        if not p or "\x00" in p:
            raise ValueError("invalid path")
        if Path(p).is_absolute():
            raise ValueError("absolute path not allowed")
        cleaned.append(p)
    candidate = (base.joinpath(*cleaned)).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("path traversal blocked")
    return candidate
