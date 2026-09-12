import re
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError

MAX_ROWS = 1000

_SELECT_RE = re.compile(r"^select\b", re.IGNORECASE)
_WITH_RE = re.compile(r"^with\b", re.IGNORECASE)
_SELECT_WORD_RE = re.compile(r"\bselect\b", re.IGNORECASE)
_EXPLAIN_SELECT_RE = re.compile(r"^explain\s+(query\s+plan\s+)?select\b", re.IGNORECASE)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_STRING_LITERAL_RE = re.compile(r"('([^']|'')*')|(\"([^\"]|\"\")*\")|(`[^`]*`)", re.DOTALL)
_DANGEROUS_FUNC_RE = re.compile(r"\b(load_extension|readfile|writefile)\s*\(", re.IGNORECASE)
# WITH...SELECT 內的 DML/DDL 關鍵字（先去字串/註解再比對，避免誤判 'delete' 字串值）
_DML_DDL_RE = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|pragma|vacuum|reindex|replace|truncate)\b",
    re.IGNORECASE,
)


def _validate_sqlite_only(connection_string: str) -> None:
    """MVP 僅允許 SQLite（與文件一致），阻擋 postgres/mysql 等 SSRF/內網橫移。"""
    try:
        url = make_url(connection_string)
    except Exception as exc:
        raise ValueError("query_error: invalid connection string") from exc
    driver = (url.drivername or "").split("+")[0].lower()
    if driver != "sqlite":
        raise ValueError("query_error: only sqlite connections are allowed in MVP")


def _sanitize_error() -> str:
    # 不回傳底層 driver 訊息，避免洩露 host/port/路徑造成掃描 oracle。
    return "connection failed or query error"


def _strip_leading_comments(sql: str) -> str:
    """移除開頭的空白、-- 行註解、/* */ 區塊註解，回到第一個有效 token。"""
    s = sql.strip()
    while True:
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1:].strip() if nl != -1 else ""
            continue
        if s.startswith("/*"):
            m = _BLOCK_COMMENT_RE.match(s)
            if not m:
                raise ValueError("query_error: unterminated block comment")
            s = s[m.end():].strip()
            continue
        return s


def _validate_select_only(sql: str) -> None:
    """唯讀限制：只允許單一 SELECT / WITH...SELECT / EXPLAIN SELECT，擋 DML/DDL 與堆疊查詢。"""
    if "\x00" in sql:
        raise ValueError("query_error: invalid character in sql")
    s = _strip_leading_comments(sql)
    if not s:
        raise ValueError("query_error: sql is empty")
    # 僅允許結尾一個分號；中間出現分號代表堆疊查詢一律拒絕。
    # （先去字串字面量再檢查，避免 WHERE name='a;b' 這類合法查詢被誤殺）
    body = s.rstrip()
    if body.endswith(";"):
        body = body[:-1].rstrip()
    _scrubbed_for_semicolon = _STRING_LITERAL_RE.sub(" ", body)
    if ";" in _scrubbed_for_semicolon:
        raise ValueError("query_error: only a single SELECT statement is allowed")
    head = _strip_leading_comments(body)
    if _SELECT_RE.match(head) or _EXPLAIN_SELECT_RE.match(head):
        pass
    elif _WITH_RE.match(head):
        # CTE：去字串/註解後不得含 DML/DDL，且必須是 WITH...SELECT（擋 WITH...DELETE/INSERT）。
        scrubbed = _STRING_LITERAL_RE.sub(" ", body)
        scrubbed = _BLOCK_COMMENT_RE.sub(" ", scrubbed)
        scrubbed = _LINE_COMMENT_RE.sub(" ", scrubbed)
        if _DML_DDL_RE.search(scrubbed):
            raise ValueError("query_error: only SELECT statements are allowed")
        if not _SELECT_WORD_RE.search(scrubbed):
            raise ValueError("query_error: only SELECT statements are allowed")
    else:
        raise ValueError("query_error: only SELECT statements are allowed")
    if _DANGEROUS_FUNC_RE.search(body):
        raise ValueError("query_error: disallowed function in SELECT")


class DBConnectionService:
    """Manages connections to external databases (SQLite only in MVP).
    Uses its own isolated engine, separate from the app's async engine.
    """

    async def test_connection(self, connection_string: str) -> dict[str, Any]:
        if not connection_string:
            return {"success": False, "error": "connection_string is empty"}
        try:
            _validate_sqlite_only(connection_string)
            engine = create_engine(connection_string, connect_args={"timeout": 5})
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return {"success": True, "error": None}
        except ValueError as exc:
            # 保留驗證類錯誤的可讀訊息（不含底層細節）
            return {"success": False, "error": str(exc)}
        except Exception:
            return {"success": False, "error": _sanitize_error()}

    async def execute_query(self, connection_string: str, sql: str, timeout: int = 10) -> dict[str, Any]:
        if not connection_string:
            raise ValueError("query_error: connection_string is empty")
        if not sql or not sql.strip():
            raise ValueError("query_error: sql is empty")
        if len(sql) > 20000:
            raise ValueError("query_error: sql too long")
        _validate_select_only(sql)
        _validate_sqlite_only(connection_string)
        try:
            engine = create_engine(connection_string, connect_args={"timeout": timeout})
            with engine.begin() as conn:
                result = conn.execute(text(sql))
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchmany(MAX_ROWS)]
                else:
                    columns = []
                    rows = []
            engine.dispose()
            return {"columns": columns, "rows": rows}
        except SQLAlchemyError as exc:
            raise ValueError(f"query_error: {_sanitize_error()}") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"query_error: {_sanitize_error()}") from exc
