# 自動化測試平台 — 啟動指南

## 系統需求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 後端運行環境 |
| Node.js | 18+ | 前端建置工具 |
| npm | 9+ | 前端套件管理 |

---

## 一、後端啟動

### 1. 建立虛擬環境（首次）

```powershell
cd automatic_test\backend
python -m venv .venv
```

### 2. 啟動虛擬環境

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

### 3. 安裝相依套件

```powershell
pip install -r requirements.txt
```

### 4. 設定環境變數

複製範本並填入實際值：

```powershell
Copy-Item .env.example .env
```

編輯 `.env`，至少填入一組 LLM API Key：

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./data/autotest.db
MEDIA_ROOT=./data/media
ROBOT_SCRIPTS_DIR=./robot_scripts
PARALLEL_MAX_WORKERS=5

# 填入至少一組
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

DEFAULT_LLM_MODEL=claude-3-5-sonnet-20241022
```

### 5. 初始化資料庫

```powershell
alembic upgrade head
```

> 資料庫檔案會建立在 `data/autotest.db`

### 6. 初始管理員帳號

資料庫初始化完成後，系統會自動建立預設管理員帳號：

| 欄位 | 值 |
|------|-----|
| 帳號 | `admin` |
| 密碼 | `admin` |
| 角色 | `admin`（最高權限）|

> **建議**：首次登入後請至後台（/admin → 帳號管理）修改預設密碼。  
> 帳號密碼也可透過 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 在初始化前預先設定。

---

### 7. （選用）安裝 Playwright 瀏覽器

Robot Framework Browser 執行真實瀏覽器測試需要此步驟：

```powershell
rfbrowser init
```

> 僅首次安裝需執行。會下載 Chromium 約 300MB。

### 8. 啟動 API Server

```powershell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API 文件可在以下位置查看：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc
- Health Check：http://localhost:8000/health

---

## 二、前端啟動

```powershell
cd automatic_test\frontend
npm install          # 首次安裝
npm run dev          # 啟動開發伺服器
```

前端運行於：http://localhost:5173

> Vite 已設定 `/api` → `http://localhost:8000` 的反向代理，前後端同時啟動即可正常使用。

---

## 三、執行測試

### 後端測試

```powershell
cd automatic_test\backend
# 確認虛擬環境已啟動

pytest                    # 執行全部測試
pytest tests/unit         # 僅執行 unit tests
pytest tests/contract     # 僅執行 contract tests
pytest tests/integration  # 僅執行 integration tests
pytest -k "test_name"     # 執行特定測試
```

### 前端測試

```powershell
cd automatic_test\frontend
npm run test              # 執行一次
npm run test:watch        # 監看模式
```

---

## 四、資料庫管理

```powershell
cd automatic_test\backend

# 查看 migration 狀態
alembic current

# 套用所有 migration
alembic upgrade head

# 回滾一個版本
alembic downgrade -1

# 產生新 migration（修改 model 後）
alembic revision --autogenerate -m "說明"
```

---

## 五、目錄結構

```
automatic_test/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI 路由（cases, checklists, executions...）
│   │   ├── core/          # 設定、資料庫連線、LLM provider
│   │   ├── models/        # SQLAlchemy ORM 模型
│   │   ├── repositories/  # 資料存取層
│   │   ├── services/      # 業務邏輯層
│   │   └── templates/     # Jinja2 HTML 報告模板
│   ├── tests/
│   │   ├── unit/          # 單元測試
│   │   ├── contract/      # API 合約測試（httpx ASGITransport）
│   │   └── integration/   # 整合測試
│   ├── alembic/           # 資料庫 migration
│   ├── data/              # SQLite DB + 媒體檔案（執行時建立）
│   ├── robot_scripts/     # Robot Framework .robot 腳本（執行時產生）
│   ├── .env               # 環境變數（需手動建立）
│   ├── .env.example       # 環境變數範本
│   └── requirements.txt   # Python 相依套件
│
└── frontend/
    ├── src/
    │   ├── components/    # Vue 元件
    │   ├── pages/         # 頁面元件
    │   ├── services/      # API 呼叫（axios）
    │   ├── stores/        # Pinia 狀態管理
    │   └── router/        # Vue Router 設定
    └── package.json
```

---

## 六、常見問題

**Q: `alembic upgrade head` 失敗**
確認 `data/` 目錄存在：
```powershell
New-Item -ItemType Directory -Force backend\data
```

**Q: 前端顯示 API 連線錯誤**
確認後端已啟動在 `http://localhost:8000`，且 `.env` 已正確設定。

**Q: AI 補齊功能沒有回應**
確認 `.env` 中至少有一組有效的 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`。

**Q: Robot Framework 測試執行失敗（無法找到瀏覽器）**
執行 `rfbrowser init` 安裝 Playwright 瀏覽器二進位檔。
