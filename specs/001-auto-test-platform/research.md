# Research: 自動化測試平台

**Phase**: 0 | **Date**: 2026-05-19 | **Plan**: [plan.md](./plan.md)

## 研究問題清單

1. LLM 多模型整合策略
2. Robot Framework 整合架構（代碼生成 + 執行 + 結果解析）
3. 媒體檔案儲存策略
4. 平行測試執行管理
5. 即時執行進度推送機制
6. Excel/CSV 測試參數解析

---

## 決策 1：LLM 多模型整合策略

**Decision**: 採用 Provider 抽象層（Protocol/ABC），初期實作 Anthropic（Claude）與 OpenAI 兩個 provider，透過設定檔切換。

**Rationale**:
- 規格要求「至少兩種主流 LLM 模型可切換」
- Provider 抽象層符合 SOLID 開放封閉原則（新增模型無需修改現有代碼）
- Anthropic SDK 與 OpenAI SDK 介面類似，抽象成本低

**Interface**:
```python
class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], max_tokens: int) -> str: ...
    async def complete_with_vision(self, messages: list[dict], media: list[bytes]) -> str: ...
```

**兩項使用場景**:
1. **AI 步驟補齊**（`ai_service.complete_steps`）：傳入已填步驟 + 媒體附件 → 回傳補齊後的步驟文字
2. **AI 代碼生成**（`ai_service.generate_robot_code`）：傳入完整測試步驟 → 回傳 Robot Framework `.robot` 文字

**Prompt 設計**:
- 步驟補齊：System prompt 描述角色為「QA 測試步驟補充助理」，few-shot 示範典型步驟格式
- 代碼生成：System prompt 包含 Robot Framework 語法規範 + 所有可用 Library（Browser Library、Playwright）

**Alternatives considered**:
- 單一固定模型：不符合規格「至少兩種可切換」
- LangChain 抽象：過重，不符 YAGNI；直接 SDK 呼叫更輕量可控

---

## 決策 2：Robot Framework 整合架構

**Decision**: 以 subprocess 呼叫 `robot` CLI 執行 `.robot` 檔，執行前先由 `ai_service.generate_robot_code()` 生成檔案，執行後解析 `output.xml`。

**架構流程**:
```
測試案例（自然語言步驟）
    │
    ▼
ai_service.generate_robot_code()
    │
    ▼
.robot 檔案（存放於 robot_scripts/generated/{case_id}_{version}.robot）
    │
    ▼
execution_service.run_case() → subprocess.run(["robot", "--outputdir", ..., case.robot])
    │
    ▼
robot_scripts/results/{execution_id}/
    ├── output.xml
    ├── log.html
    ├── report.html
    └── screenshots/*.png / videos/*.mp4
    │
    ▼
report_service.parse_xml(output.xml) → ExecutionRecord + TestReport 寫入 DB
```

**Robot Framework Library 選擇**:
- `robotframework-browser` (Playwright-based)：支援截圖、影片錄製，現代化選擇
- 截圖：RF Browser 的 `Take Screenshot` 關鍵字（每個步驟可自動截圖）
- 影片錄製：RF Browser 的 `New Context` 設定 `record_video=True`

**XML 解析**:
- 使用 Python 內建 `xml.etree.ElementTree` 解析 `output.xml`
- 關鍵結構：`<suite>` → `<test>` → `<kw>` → `<status>`
- 擷取：每個 test 的 status（PASS/FAIL）、elapsedtime、message（失敗訊息）
- 截圖路徑從 XML `<msg>` 或 `<tag>` 中提取

**代碼快取策略**:
- 相同 `case_id + version` 的 .robot 檔若已存在則跳過生成（避免重複 LLM 呼叫）
- 案例版本遞增時清除舊快取並重新生成

**Alternatives considered**:
- `robotframework-selenium`：較舊，不支援原生影片錄製
- 直接呼叫 Playwright Python：繞過 RF，失去 RF 關鍵字結構與 XML 報告

---

## 決策 3：媒體檔案儲存策略

**Decision**: 本地檔案系統（設定化路徑），分三類目錄管理。

**目錄結構**:
```
{MEDIA_ROOT}/
├── attachments/             # 建立測試案例時上傳的圖片/影片/網址快取
│   └── {case_id}/
│       ├── {filename}
│       └── ...
└── execution_results/       # 測試執行過程中擷取的截圖/影片
    └── {execution_id}/
        ├── screenshots/
        └── videos/
```

**DB 中只存路徑，不存 Blob**（符合 KISS 原則）。

**API 服務**:
- `GET /media/attachments/{case_id}/{filename}` → 串流回應
- `GET /media/results/{execution_id}/{type}/{filename}` → 截圖直接回傳；影片使用 HTTP Range request 串流

**大小限制**（在 FastAPI middleware 層驗證）:
- 圖片：≤10MB，允許 .jpg/.png/.gif/.webp
- 影片：≤100MB，允許 .mp4/.webm
- 網址：僅驗證格式，不下載

**Alternatives considered**:
- S3/MinIO：過重，初期本地存取即可，介面已抽象，未來可替換
- DB Blob：性能差，備份複雜

---

## 決策 4：平行測試執行管理

**Decision**: 使用 **pabot（robotframework-pabot）** 執行平行測試，一次清單執行對應一個 `pabot` 指令。

**架構**:
```
清單執行請求
    │
    ▼
execution_service.run_checklist()
    │  為每個 ChecklistItem 產生對應的 .robot 檔案
    │  robot_scripts/generated/{execution_id}/{case_id}_{version}.robot
    │
    ▼
asyncio.create_subprocess_exec(
    "pabot",
    "--processes", str(max_workers),
    "--listener", "src/execution/listener.py:ExecutionListener:{execution_id}",
    "--outputdir", f"robot_scripts/results/{execution_id}",
    *[str(f) for f in robot_files]
)
    │
    ▼
ExecutionListener（RF Listener Plugin）監聽事件
    → 每個 start_test / end_test 寫入 asyncio.Queue
    → FastAPI SSE endpoint 讀取 Queue 推送至前端
    │
    ▼
pabot 完成後解析 output.xml
    → 更新 CaseResult 狀態 + ExecutionRecord 統計
```

**執行狀態管理**:
- `ExecutionRecord.status`：`pending | running | completed | failed`
- `CaseResult.status`：`passed | failed | timeout | error | skipped`
- DB 狀態由 ExecutionListener 在 `end_test` 時即時更新

**逾時處理**:
- pabot 本身支援 `--timeout` 參數設定每個 test 的上限
- 或由外層 `asyncio.wait_for(pabot_process, timeout=N)` 控制整體執行時間上限

**Alternatives considered**:
- asyncio.Semaphore + subprocess per case：需自行管理程序池，pabot 提供現成的並行管理與 output.xml 合併
- Celery：過重，引入 broker 複雜度；單機部署使用 pabot 已足夠

---

## 決策 5：即時執行進度推送機制

**Decision**: Server-Sent Events (SSE) + **RF Listener Plugin** — SSE 負責前端推送，Listener Plugin 負責從 pabot 取得結構化事件。

**RF Listener Plugin（事件來源）**:
```python
# src/execution/listener.py
class ExecutionListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._queue = get_execution_queue(execution_id)  # 從全域 registry 取得 asyncio.Queue

    def start_test(self, name, attrs):
        self._queue.put_nowait({
            "event": "case_started",
            "execution_id": self.execution_id,
            "case_name": name,
        })

    def end_test(self, name, attrs):
        self._queue.put_nowait({
            "event": "case_completed",
            "execution_id": self.execution_id,
            "case_name": name,
            "status": attrs["status"],  # PASS / FAIL
            "elapsed_ms": int(attrs["elapsedtime"]),
            "message": attrs.get("message", ""),
        })
```

**FastAPI SSE endpoint（事件消費）**:
```python
@router.get("/executions/{execution_id}/stream")
async def stream_execution(execution_id: str):
    queue = get_execution_queue(execution_id)

    async def event_generator():
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("event") in ("execution_completed", "execution_error"):
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**全域 Queue Registry**:
```python
_queues: dict[str, asyncio.Queue] = {}

def get_execution_queue(execution_id: str) -> asyncio.Queue:
    if execution_id not in _queues:
        _queues[execution_id] = asyncio.Queue()
    return _queues[execution_id]
```

**前端**:
```typescript
const evtSource = new EventSource(`/api/v1/executions/${id}/stream`)
evtSource.onmessage = (e) => store.updateProgress(JSON.parse(e.data))
evtSource.addEventListener("execution_completed", () => evtSource.close())
```

**Alternatives considered**:
- WebSocket：雙向通訊，適合聊天應用；這裡只需服務端推送，SSE 夠用且更簡單
- Polling：每秒 GET 請求，效率低且產生大量無效請求
- 輪詢 pabot stdout：比解析文字輸出更脆弱，RF Listener 提供結構化事件

---

## 決策 6：Excel/CSV 測試參數解析

**Decision**: 使用 `openpyxl`（Excel）+ 內建 `csv` 模組（CSV）+ 自訂 Tab-分隔解析（文字檔），統一轉換為 `list[dict]` 結構。

**解析流程**:
1. 讀取上傳檔案的第一列為標頭（欄位名）
2. 與測試案例的測試資料欄位名稱做模糊比對（降低大小寫、去空白）
3. 回傳預覽資料（前 10 列）供使用者確認
4. 使用者確認後，逐列寫入 `TestData` 記錄

**欄位對應邏輯**:
- 精確比對：標頭名 == 測試資料欄位名 → 直接對應
- 模糊比對：`difflib.SequenceMatcher` 相似度 ≥0.8 → 提示使用者確認
- 無法對應 → 提示標頭名並請使用者手動選擇目標欄位

**Alternatives considered**:
- `pandas`：功能過重，僅需簡單解析；openpyxl + csv 足夠且依賴更輕

---

---

## 決策 7：測試案例編號自動生成策略（Session 2026-06-13）

**Decision**: 後端在建立測試案例時，根據 `system_category` 查詢**同前綴的最大現有序號**（含已軟刪除者以防 reuse），加 1 後格式化為三位數，組合為 `{system_category}-{NNN}`。若 `system_category` 為空則使用預設前綴 `TC`。

**Rationale**:
- 符合 spec：「編號由系統別+三位數序號組成，序號從 001 開始往後遞增，在同一系統別內保持唯一性」（Clarifications Session 2026-06-13）
- 查詢含軟刪除案例的最大號碼，防止刪除後重複使用
- 不依賴 DB auto-increment，因為編號前綴與 system_category 繫結

**Implementation sketch**:
```python
# In CaseService.generate_case_number()
async def generate_case_number(self, system_category: str) -> str:
    prefix = (system_category or "TC").strip()
    # Query all (including soft-deleted) to avoid reuse
    cases = await self.repo.list_by_prefix(prefix)
    max_num = 0
    for c in cases:
        parts = c.case_number.rsplit("-", 1)
        if len(parts) == 2 and parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
    return f"{prefix}-{str(max_num + 1).zfill(3)}"
```

**Alternatives considered**:
- DB sequence per system_category：需額外表格，過度複雜
- UUID：不符合 spec 要求
- Client-side generation：並行操作有競態條件風險

---

---

## 決策 8：RF Script 實體檔案儲存策略（Session 2026-06-20）

**Decision**: RF 程式碼儲存為實體 `.robot` 檔案，路徑格式為 `{ROBOT_SCRIPTS_DIR}/{case_number}.robot`，透過 `PUT /cases/{id}/robot-script` 持久化，執行時由背景任務直接讀取。

**Rationale**:
- Robot Framework CLI（`robot` / `pabot`）執行時需要實體 `.robot` 檔案作為輸入，無法直接餵入字串
- 持久化為檔案可避免每次執行前重新生成 LLM 代碼（零延遲，符合 FR-016 規格）
- `{case_number}.robot` 命名讓運維人員可直接對應案例，易於除錯
- 相較於存入 DB TEXT 欄位再臨時寫出，直接持久化更符合 KISS 原則

**流程**:
```
Tab 2 Chat → AI 生成 RF 代碼 → 使用者點「儲存 RF 程式碼」
    → PUT /cases/{id}/robot-script
    → backend 寫入 {ROBOT_SCRIPTS_DIR}/{case_number}.robot
    → 執行時 execution_service 讀取該檔案傳給 Robot Framework
```

**Frontend 整合**:
- `RFCodePreview` 元件新增 `case-id` prop
- 進入頁面時呼叫 `GET /cases/{id}/robot-script` 自動載入已儲存腳本
- 「儲存 RF 程式碼」按鈕（紫色）觸發 `PUT /cases/{id}/robot-script`

**Alternatives considered**:
- DB TEXT 欄位（`TestCase.robot_code`）：需 schema 遷移 + 每次執行仍需寫出臨時檔案，兩步驟不如直接持久化
- 執行時即時 LLM 生成：受 SC-010 35 秒限制，大清單執行延遲不可接受

---

## 決策 9：SSE Polling Session 隔離策略（Session 2026-06-20）

**Decision**: SSE `/executions/{id}/stream` endpoint 每次輪詢都建立全新的 `AsyncSessionLocal()` session，而非重用 request-scoped `get_db()` session。

**Root Cause**:
SQLite 的 WAL 模式下，同一個 session 在第一次 `SELECT` 時開啟 read transaction，後續所有 `SELECT` 看到的是該 transaction 開始時的快照。背景任務（`_execute_all_cases_bg`）在自己的 session 中 commit "completed"，但 SSE 的 session 因快照隔離看不到更新 → 60 輪輪詢後 timeout → 前端收到 `execution_error`。

**Fix**:
```python
# 每輪輪詢開新 session，確保看到最新 DB 狀態
async with AsyncSessionLocal() as poll_session:
    poll_repo = ExecutionRepository(poll_session)
    updated = await poll_repo.get(execution_id)
if updated and updated.status in ("completed", "failed", "error"):
    ...
```

同時將輪詢上限從 60 秒延長至 120 秒，`execution_error` 的 field 改為 `message`（與前端 store 期望一致）。

**Alternatives considered**:
- `session.refresh(record)`：強制重新讀取，但 SQLite read transaction 仍在同一 snapshot 中，無法解決根本問題
- `expire_on_commit=True`：只影響 commit 後的 expire 行為，對 read-only polling session 無效

---

## 決策 10：背景執行任務 Session 管理（Session 2026-06-20）

**Decision**: 所有在 HTTP request 生命週期之外執行的資料庫操作（`asyncio.create_task` 觸發的背景任務），必須透過 `async with AsyncSessionLocal() as session` 建立自己的 session，嚴禁重用 `get_db()` 提供的 request-scoped session。

**Root Cause**:
`get_db()` 使用 `async with AsyncSessionLocal() as session` + `yield`，HTTP response 回傳後 `get_db` 執行 `await session.commit()`，session 進入 `'prepared'` 狀態。後續若背景任務試圖在此 session 上執行 SQL，SQLAlchemy 拋出 `InvalidRequestError: This session is in 'prepared' state`。

**Fix**:
```python
# 在 run_checklist_parallel 中：先提取純 Python 資料再建立 task
case_ids = [item.test_case_id for item in checklist.items]  # 在 session 關閉前提取
asyncio.create_task(ExecutionService._execute_all_cases_bg(record.id, case_ids, concurrency))

# 背景任務為 @staticmethod，完全不持有 request session 的參考
@staticmethod
async def _execute_all_cases_bg(execution_id: str, case_ids: list[str], ...) -> None:
    async with AsyncSessionLocal() as session:  # 自己的 session
        ...
    async with AsyncSessionLocal() as session:  # 結束時再開新 session 更新狀態
        await exec_repo.update_status(...)
        await session.commit()
```

---

---

## 決策 11：RF 原生執行報告持久化與服務策略

**Decision**: RF 執行完成後，在 `tempfile.TemporaryDirectory` 刪除前，將整個 output 目錄複製到持久化路徑 `data/execution_reports/{execution_id}/`；後端提供靜態檔案路由服務，前端以 `<iframe>` 嵌入。

**架構說明**:
```
RF 執行（subprocess）
    ↓  生成至 --outputdir {tmp}/
       output.xml, log.html, report.html
       browser/screenshots/*.png（embedded 至 log.html base64 by RF Browser）
    ↓  執行完成，解析 output.xml
    ↓  shutil.copytree(output_dir, settings.execution_reports_dir / execution_id)
    ↓  tempdir 安全釋放

GET /executions/{id}/rf-report/{filename}
    → FileResponse("data/execution_reports/{id}/{filename}")

前端 ResultPage.vue
    → <iframe :src="`/api/v1/executions/${id}/rf-report/log.html`" />
    → <iframe :src="`/api/v1/executions/${id}/rf-report/report.html`" />
```

**適用範圍**:
- 清單執行（`_run_pabot` / `_run_sequential`）：`--outputdir` 已在 tmp_dir 下，copy 整個 output_dir
- 試跑（`_execute_trial_bg`）：`_run_single_case_with_timeout` 使用 tmp_dir，在 `with` block 結束前 copy

**截圖路徑問題**:
- RF Browser 庫預設將截圖以 base64 inline 方式嵌入 log.html（`Embed Screenshots` 設定為 True 時）
- 若截圖為外部參照：copy 時同步複製 browser/ 子目錄，相對路徑在 iframe 中仍有效
- 建議執行時設定 `BROWSER_EMBED_SCREENSHOTS=True` 以消除相對路徑問題

**兩種報告類型說明（不可混淆）**:
- **FR-011 匯出報告**：`GET /executions/{id}/export` → 後端 Jinja2 模板渲染 → 一個自包含 HTML 可下載
- **FR-010/FR-019 嵌入報告**：`GET /executions/{id}/rf-report/{filename}` → RF 原生 log.html/report.html → 前端 `<iframe>` 嵌入

**Rationale**:
- 直接使用 RF 原生報告，不重造輪子；log.html 的步驟折疊、截圖 lightbox、時間軸均由 RF 提供
- 靜態檔案服務比動態代理簡單，無需 streaming proxy
- `shutil.copytree` 原子性足夠，失敗僅影響報告顯示而不影響執行結果

**Alternatives considered**:
- 直接將 RF `--outputdir` 指向持久化路徑：避免複製，但並行執行時若多案例共用目錄會互相覆蓋
- 動態代理（proxy 整個 tmpdir）：tmpdir 生命週期與 HTTP 請求不一致，不可行
- 路徑重寫（rewrite log.html 內部相對路徑）：複雜且脆弱，不優先

---

## 決策 12：身份驗證與角色授權架構（Session 2026-06-21）

**Decision**: 帳號密碼 + JWT Token（`python-jose[cryptography]`）+ `passlib[bcrypt]` 密碼雜湊；三角色 RBAC（`admin` / `editor` / `viewer`）透過 FastAPI Depends 中間件執行；前端 Vue Router `beforeEach` guard 檢查 JWT 有效性。

**Rationale**:
- JWT stateless 符合現有 FastAPI 架構，無需 session store
- `python-jose` 是 FastAPI 官方文件推薦的 JWT 庫，與 `passlib[bcrypt]` 搭配為 Python 生態標準做法
- 三角色足以覆蓋 FR-025 需求，且後續擴充容易（JWT payload 增加 `role` claim 即可）

**JWT 架構**:
```python
# backend/src/core/security.py
from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = settings.JWT_SECRET_KEY  # 從 .env 讀取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"])

def create_access_token(sub: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": sub, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
```

**FastAPI Auth Dependencies**:
```python
# backend/src/core/dependencies.py（新增）
async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user = await user_repo.get_by_username(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401)
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user

async def require_editor_or_above(user: User = Depends(get_current_user)) -> User:
    if user.role == "viewer":
        raise HTTPException(403, "Editor or Admin required")
    return user
```

**前端 Router Guard**:
```typescript
// frontend/src/router/index.ts
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.meta.requiresAdmin && getUserRole() !== 'admin') return '/'
})
```

**角色權限矩陣**:
| 功能 | admin | editor | viewer |
|------|-------|--------|--------|
| 瀏覽測試案例 / 清單 | ✅ | ✅ | ✅ |
| 建立 / 編輯 / 刪除案例 | ✅ | ✅ | ❌ |
| 建立 / 編輯 / 刪除清單 | ✅ | ✅ | ❌ |
| 執行測試清單 | ✅ | ✅ | ✅ |
| 管理後台（/admin） | ✅ | ❌ | ❌ |

**初始管理員 Seed**:
```python
# backend/scripts/seed_admin.py
# 執行方式：python -m scripts.seed_admin
# 從 .env 讀取 ADMIN_USERNAME / ADMIN_PASSWORD
```

**Token 儲存**:
- 前端 `localStorage`（簡單、SPA 標準）
- 後端無 refresh token（初期；Token 有效期 8 小時，到期重新登入）

**Alternatives considered**:
- Session Cookie：需 server-side session store（Redis），增加部署複雜度
- SSO / OAuth：超出現階段需求，未來可替換
- PyJWT 直接使用：`python-jose` 額外提供 JWS/JWE 支援，且為 FastAPI 生態標準

---

## 決策 13：RF 程式碼變數自動解析策略（Phase 26）

**Decision**: 前端純正規式解析，不引入 RF parser 函式庫；使用 hardcoded exclusion set 排除 RF 框架內建變數。

**Rationale**:
- RF 變數語法固定（`${VAR_NAME}`），正規式足以覆蓋所有使用場景
- 引入完整 RF parser（如 robotframework Python 套件）會大幅增加前端 bundle 體積
- Exclusion set 維護成本低，RF 內建變數清單穩定（不隨 RF 版本頻繁變動）
- 此功能為「輔助補齊」性質，不需 100% 精確，漏偵測 edge case 可由使用者手動補充

**解析流程（前端 TypeScript）**:
```typescript
const RF_BUILTINS = new Set([
  'CURDIR', 'EXECDIR', 'TEMPDIR', 'OUTPUT_DIR', 'OUTPUT_FILE',
  'LOG_FILE', 'REPORT_FILE', 'DEBUG_FILE', 'SUITE_NAME', 'SUITE_SOURCE',
  'SUITE_DOCUMENTATION', 'SUITE_STATUS', 'SUITE_MESSAGE', 'TEST_NAME',
  'TEST_DOCUMENTATION', 'TEST_STATUS', 'TEST_MESSAGE', 'PREV_TEST_NAME',
  'PREV_TEST_STATUS', 'PREV_TEST_MESSAGE', 'LOG_LEVEL',
  'True', 'False', 'None', 'null', 'EMPTY', 'SPACE',
])

function extractRFVariables(rfCode: string): string[] {
  const matches = rfCode.matchAll(/\$\{([^}]+)\}/g)
  const seen = new Set<string>()
  const result: string[] = []
  for (const m of matches) {
    const name = m[1]
    if (!RF_BUILTINS.has(name) && !seen.has(name.toUpperCase())) {
      seen.add(name.toUpperCase())
      result.push(name)
    }
  }
  return result
}
```

**合併策略**:
- `field_name` = 提取的名稱（去除 `${}`，保留原始大小寫）
- `rf_variable` = `${原始名稱}`（與 RF 程式碼完全一致）
- 以 `rf_variable` 大小寫不分比對現有 `editTestData`，已存在者略過
- API 失敗（404 = 尚無 RF 程式碼）時靜默略過，不中斷進入編輯模式的流程

**Alternatives considered**:
- robotframework-parser npm 套件：過重，且此場景不需語法樹解析
- 後端提供「解析 RF 變數」端點：過度設計，前端正規式即可滿足需求
- 詢問使用者是否要「取代」或「合併」：已決定固定採合併補齊策略，不增加 UX 複雜度

---

---

## 決策 14：Chat 訊息 `type` 欄位設計（Phase 27）

**Decision**: ChatMessage 新增 `type: Enum` 欄位，分為兩種訊息型別：
- `chat`：一般使用者與 AI 的對話訊息
- `trial_run_result`：試跑結果訊息（系統自動生成）

**Rationale**:
- Tab 2 立即試跑功能需區分「使用者對話」與「系統試跑報告」，前端渲染邏輯不同
- 試跑結果訊息不需要使用者的 sender 身份，而是系統發送的結構化結果
- 持久化時使用 `type` 欄位可便於未來查詢與統計（如「某案例有多少試跑記錄」）

**實作細節**:
- 資料庫：`ChatMessage.type: VARCHAR(20)` 非 null，預設 `'chat'`
- ORM（Alembic migration）：新增欄位並新增 CHECK 約束或使用 Enum 類型（SQLAlchemy 層）
- 既有訊息應補全為 `type='chat'`（migration 中 SET）
- API response 均包含 `type` 欄位，前端根據 `type` 決定渲染樣式

**Alternatives considered**:
- 獨立表 `TrialRunResult`：過度複雜，試跑結果本質就是對話歷史的一部分
- 在 content 中嵌入 metadata（如 JSON `{type: "trial_run"}`）：解析複雜且容易出錯，不符 KISS 原則

---

## 決策 15：Trial Run Result 訊息格式規範（Phase 27）

**Decision**: 試跑結果訊息（`type: "trial_run_result"`）的內容結構化為 JSON 物件，包含以下欄位：

```json
{
  "status": "passed" | "failed" | "timeout" | "error",
  "elapsed_ms": 12345,
  "error_message": "...",
  "screenshot_paths": ["path/to/screenshot1.png", "path/to/screenshot2.png"]
}
```

**欄位說明**:
- `status`：執行結果狀態
  - `passed`：全部步驟通過
  - `failed`：某個步驟失敗
  - `timeout`：執行逾時
  - `error`：系統內部錯誤（非測試邏輯失敗）
- `elapsed_ms`：執行耗時（毫秒）
- `error_message`：若 `status` 為 `failed`，包含失敗步驟的錯誤訊息；`passed` 時為空
- `screenshot_paths`：失敗時擷取的截圖路徑陣列（最多 1-3 張），相對路徑（如 `executions/{execution_id}/screenshots/...`）

**前端渲染**:
- 在 Chat 氣泡中顯示 badge（綠色 PASS / 紅色 FAIL）+ 執行時間
- 展開區域顯示錯誤訊息 + 截圖廊道
- 截圖可點擊放大

**Rationale**:
- 明確的 JSON 結構便於版本化與未來擴展（如添加其他 metadata）
- `screenshot_paths` 相對化可支援媒體搬遷
- 格式與 ExecutionRecord XML 解析結果一致，降低轉換成本

**Alternatives considered**:
- 純文字拼接（如 "PASS in 123ms"）：不易擴展
- 嵌入完整截圖 base64：DB 記錄過大，首頁載入變慢

---

## 決策 16：AI 自動分析失敗原因 Prompt 策略（Phase 27）

**Decision**: 試跑失敗時，後端自動組裝包含失敗訊息的提示詞，觸發 AI 服務分析失敗原因並回應修正建議。

**Prompt 結構**:
```
[System]
你是 QA 自動化測試顧問。使用者提供了一份 Robot Framework 測試的執行結果。
請分析失敗原因，並提供修正建議（包括新的 RF 程式碼片段或步驟描述）。

[User]
測試案例: {case_name}
執行時間: {elapsed_ms}ms
執行狀態: {status}

失敗訊息:
{error_message}

當前 RF 程式碼:
```robot
{current_rf_code}
```

請分析失敗原因並提供修正建議。
```

**流程**:
1. 試跑完成，`status = "failed"`
2. 後端呼叫 `ExecutionService._generate_trial_run_analysis_prompt()` 組裝提示詞
3. 調用 `ai_service.complete(messages=[...], max_tokens=1500)` 獲取 AI 回應
4. AI 回應作為新的 ChatMessage（`type: "chat"`）自動附加到對話歷史
5. 前端接收後顯示 AI 建議，使用者可直接修改步驟或 RF 程式碼

**Rationale**:
- 提示詞結構化明確，不易誤解
- 包含原始 RF 程式碼供 AI 上下文理解
- 自動觸發降低使用者操作步驟
- AI 回應作為 `type: "chat"` 訊息而非 `trial_run_result`（區分系統自動 vs 使用者主動對話）

**邊界案例**:
- 若 `error_message` 為空（系統錯誤如逾時），提示詞自動簡化為「請檢查步驟是否符合預期」
- 若 AI 服務超時（超過 SC-010 的 35 秒限制），不阻斷試跑流程，直接返回試跑結果而不附加 AI 建議
- Prompt 長度超過模型限制時，自動截斷 `error_message` 的末尾

**Alternatives considered**:
- 使用者手動點擊「詢問 AI」按鈕才分析：增加操作步驟，用戶體驗差
- 將分析結果存在 TrialRunResult.analysis 欄位：破壞單一職責原則，ChatMessage 已是對話記錄容器
- 使用 fine-tuned 模型：成本高，通用 Claude 模型已足以勝任此任務

---

## 所有 NEEDS CLARIFICATION 解析完畢

| 問題 | 決策 |
|------|------|
| LLM 多模型 | Provider 抽象層，初期 Anthropic + OpenAI |
| RF 整合 | pabot 執行 + RF Listener Plugin + XML 解析 + RF Browser |
| 媒體儲存 | 本地檔案系統，路徑設定化 |
| 平行執行 | **pabot（robotframework-pabot）**，一個清單執行 = 一個 pabot 指令 |
| 即時進度 | SSE + **RF Listener Plugin**（`start_test`/`end_test` → asyncio.Queue） |
| Excel/CSV | openpyxl + csv，標頭比對 + 預覽確認 |
| 案例編號生成 | system_category 前綴 + 三位數序號，查最大值+1 |
| RF 代碼生成時機 | Tab 2 Chat 生成後存入 DB；執行時直接取用，無存檔時回退即時生成 |
| 清單案例管理 | 獨立畫面 /checklists/:id/cases，支援新增/移除/排序/備註 |
| RF script 儲存 | 實體檔案 `{ROBOT_SCRIPTS_DIR}/{case_number}.robot`，PUT API 持久化 |
| SSE session 隔離 | 每輪輪詢 `AsyncSessionLocal()` 新 session，避免 SQLite transaction snapshot |
| 背景任務 session | `@staticmethod` + 自建 `AsyncSessionLocal`，禁止重用 request-scoped session |
| RF 報告持久化 | 執行後 `shutil.copytree` 至 `data/execution_reports/{id}/`，FastAPI FileResponse 服務，iframe 嵌入 |
| Auth / Admin RBAC | JWT Token（python-jose + passlib bcrypt），三角色（admin/editor/viewer），FastAPI Depends + Vue Router guard |
| Chat `type` 欄位 | 區分 `chat` 與 `trial_run_result`，持久化區分訊息類型 |
| Trial run result 格式 | JSON：status / elapsed_ms / error_message / screenshot_paths |
| AI 失敗分析 prompt | 自動組裝失敗訊息供 AI 分析，回應作為新 ChatMessage 附加 |
