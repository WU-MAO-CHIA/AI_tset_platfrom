# 自動化測試平台

一站式的自動化測試平台：建立測試案例、組成測試清單、以 Robot Framework 執行，並查看報告。以下先介紹功能，再說明如何啟動。

## 功能總覽

| 功能 | 說明 |
|------|------|
| 測試案例與清單 | 建立案例（可用 AI 補齊步驟、上傳 RF 腳本），組成清單後一次執行；清單列表顯示每份清單最近 10 次的結果條 |
| 執行佇列 | 執行請求存進資料庫排隊，重啟後端不會遺失；同時執行的數量由 `EXECUTION_MAX_CONCURRENT`（預設 1）控制，試跑優先於清單。執行中可取消，即時進度從資料庫讀取 |
| 排程執行（`/schedules`） | 為清單設定每天、每週或固定間隔（至少 15 分鐘）自動執行。後端停機錯過的排程補跑一次；上一輪還在跑就跳過這一輪。時區由 `SCHEDULE_TIMEZONE`（預設 `Asia/Taipei`）設定，`SCHEDULE_ENABLED=false` 可關閉 |
| 監控儀表板（`/dashboard`） | 僅管理員可見，顯示目前佇列、執行中的測試與排程狀態 |
| 驗證碼辨識 | RF 腳本中的 CAPTCHA 關鍵字交給後端呼叫 LLM 辨識，執行測試的環境不需要 LLM 金鑰 |
| 隔離執行（runner 容器） | Docker 部署時，測試腳本在獨立的 `runner` 容器以低權限使用者執行，碰不到後端的金鑰與資料庫 |
| 執行環境（`/runner-environments`） | 管理員登記多台 runner（Linux 容器或 Windows 主機，token 加密保存），內建的 `runner` 容器顯示為「預設容器」。案例選擇預設環境，試跑、清單執行與排程可改選同類型的其他環境；清單中不同環境的案例會同時在各自的環境執行。Windows 主機安裝見 [docs/windows-runner.md](docs/windows-runner.md) |
| 帳號與權限 | admin / editor / viewer 三種角色；登入閒置 `JWT_EXPIRE_MINUTES`（預設 10 分鐘）未操作會自動登出，有操作就自動續期 |

### 安全性設定

- `APP_ENV=prod` 時，後端會拒絕以預設或不足 32 字元的 `JWT_SECRET_KEY`、預設的 `ADMIN_PASSWORD` 啟動，登入 cookie 也會加上 `Secure`。
- 改密碼、改角色或停用帳號後，該帳號已發出的 token 會立即失效。

## 系統需求
以 Docker 執行只需要 Docker Desktop；在本機直接開發才需要 Python、Node.js、npm。

| 工具 | 版本 | 用途 |
|------|------|------|
| Docker Desktop | 含 Compose v2 | 以容器執行（見「快速開始：使用 Docker 執行」） |
| Python | 3.11+ | 後端運行環境（本機開發） |
| Node.js | 18+ | 前端建置工具（本機開發） |
| npm | 9+ | 前端套件管理（本機開發） |

---

## 快速開始：使用 Docker 執行

前後端都在容器中執行，不需要在本機安裝 Python、Node.js 或瀏覽器。

### 1. 開啟 Docker Desktop

確認 Docker Desktop 已在執行（`docker info` 能正常回應）。

### 2. 設定 `backend/.env`

容器與本機開發共用同一份設定檔：

```powershell
Copy-Item backend\.env.example backend\.env   # 已經有 .env 就略過
```

需要填寫的欄位：

| 欄位 | 說明 |
|------|------|
| `JWT_SECRET_KEY` | 至少 32 字元的固定隨機字串；一旦更換，已登入的使用者都必須重新登入 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 初始管理員帳號，容器第一次啟動時自動建立 |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | 至少填一組，AI 功能才能使用 |
| `APP_ENV` | `dev` 或 `prod`；`prod` 會拒絕以預設的 `JWT_SECRET_KEY`、`ADMIN_PASSWORD` 啟動 |
| `OLLAMA_BASE_URL` | （選用）使用主機上的 Ollama 時填 `http://host.docker.internal:11434` |

`DATABASE_URL`、`MEDIA_ROOT`、`ROBOT_SCRIPTS_DIR` 由 `docker-compose.yml` 固定為容器內的路徑，`.env` 裡的值不會影響容器。

另外在**專案根目錄**的 `.env`（docker compose 讀的，和 `backend/.env` 不同）產生 `RUNNER_TOKEN`，後端用它把測試交給 runner 容器：

```powershell
Add-Content .env "RUNNER_TOKEN=$([guid]::NewGuid().ToString('N'))$([guid]::NewGuid().ToString('N'))"
```

測試腳本在獨立的 `runner` 容器執行，那裡沒有後端的金鑰與資料庫；本機直接開發（不用 Docker）時則由後端自己執行。

### 3. 建置並啟動

```powershell
docker compose up -d --build
```

第一次建置需要下載瀏覽器，約需數分鐘。完成後確認狀態，`backend` 應顯示 `healthy`（`frontend` 會等 `backend` 就緒才啟動）：

```powershell
docker compose ps
```

### 4. 開啟網頁

瀏覽 http://localhost:8080 ，以 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 登入。

### 常用操作

```powershell
docker compose logs -f backend      # 查看後端 log（啟動失敗時先看這裡）
docker compose up -d --build        # 修改程式碼後，重新建置並啟動
docker compose up -d                # 修改 backend/.env 後重新建立容器（restart 不會重新讀取 .env）
docker compose down                 # 停止服務（保留資料）
docker compose down -v              # 停止並刪除所有資料（資料庫、附件、腳本）
```

改用其他 port（預設 8080）：

```powershell
$env:FRONTEND_PORT = "9090"; docker compose up -d
```

### 架構與資料

| 服務 | 說明 |
|------|------|
| `frontend` | nginx 提供前端網頁，並把 `/api` 轉給後端；對外 port 預設 8080 |
| `backend` | FastAPI，不對外開放 port。每次啟動會自動套用資料庫 migration，並在帳號不存在時建立初始 admin；執行佇列與排程器也在這裡執行 |
| `runner` | Robot Framework + Playwright，負責實際執行測試。只拿到 `RUNNER_TOKEN`，沒有 `backend/.env`、不掛資料 volume，並限制記憶體、CPU 與權限 |

資料存放在 Docker volume，`docker compose down` 不會刪除：

- `backend-data`：資料庫、附件、執行報告
- `robot-scripts`：產生的 .robot 腳本

容器的資料與本機開發的 `backend/data/` 是分開的，第一次啟動會是全新的資料庫。

### 注意事項

- **使用 `APP_ENV=prod` 時**：登入 cookie 會帶 `Secure`。若用 `http://` 從 localhost 以外的位址連線，測試執行的即時進度無法顯示，需改用 HTTPS。
- **容器內的 `localhost` 指的是容器本身**，不是你的電腦；要連主機上的服務請用 `host.docker.internal`。
- **後端只能執行一個實例**：佇列存在資料庫裡，但取出執行的 worker 與排程器在後端程序內，SQLite 也只適合單一實例，請勿水平擴充 `backend` 服務。

### 部署到雲端主機

免費部署到 Oracle Cloud Always Free 的 ARM VM（含 HTTPS 與備份），見 [docs/deploy-oracle.md](docs/deploy-oracle.md)。

要測只能在 Windows 執行的桌面程式，另外準備一台 Windows 電腦當 runner，見 [docs/windows-runner.md](docs/windows-runner.md)。

### 常見問題

**Q: docker 指令出現 `failed to connect to the docker API ... dockerDesktopLinuxEngine`**
Docker Desktop 沒有在執行。開啟後等它顯示 running 再重試。

**Q: 出現 `env file ... backend/.env not found`**
尚未建立 `backend/.env`，依上方步驟 2 建立。

**Q: `docker compose ps` 中 `backend` 一直不是 `healthy`**
執行 `docker compose logs backend` 查看原因。常見的是 `JWT_SECRET_KEY` 不足 32 字元，或 `APP_ENV=prod` 時仍使用預設的 `JWT_SECRET_KEY` / `ADMIN_PASSWORD`。

**Q: 啟動時顯示 port 8080 已被占用**
改用其他 port，見上方「改用其他 port」。

---

## 一、後端啟動

### 1. 建立虛擬環境（首次）

```powershell
cd backend
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
pip install -r requirements-dev.txt   # 執行測試（pytest）必需
```

### 4. 設定環境變數

複製範本並填入實際值：

```powershell
Copy-Item .env.example .env
```

編輯 `.env`，至少填入一組 LLM API Key，並務必自行設定 `JWT_SECRET_KEY`：

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./data/autotest.db
MEDIA_ROOT=./data/media
ROBOT_SCRIPTS_DIR=./robot_scripts
PARALLEL_MAX_WORKERS=5
# 同時執行幾筆清單／試跑，其餘排隊（試跑優先）；單一清單內的平行度由 PARALLEL_MAX_WORKERS 限制
EXECUTION_MAX_CONCURRENT=1
# 排程時間的時區（IANA 名稱）；SCHEDULE_ENABLED=false 可關閉排程器
SCHEDULE_TIMEZONE=Asia/Taipei
SCHEDULE_ENABLED=true

# 填入至少一組
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# 後台「目前啟用模型」未設定時的 fallback
DEFAULT_LLM_MODEL=claude-sonnet-5

# 本地 Ollama 原生 API base URL（留空＝不啟用本地模型）
OLLAMA_BASE_URL=http://localhost:11434

# 必須設定為固定值，否則每次重啟 API Server 都會讓既有登入 token 失效（造成 401）
JWT_SECRET_KEY=change-me-to-a-strong-random-secret-key
# 閒置逾時（分鐘）：有操作就自動續期，閒置超過才需重新登入
JWT_EXPIRE_MINUTES=10

# dev | prod | test；prod 拒絕預設的 secret／密碼並啟用 Secure cookie
APP_ENV=dev

# 初始管理員帳號（供 scripts/seed_admin.py 使用，見下方步驟 6）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

本機開發時測試由後端自己執行（`EXECUTION_RUNNER` 預設為 `local`），不需要 runner 容器與 `RUNNER_TOKEN`。

### 5. 初始化資料庫

```powershell
alembic upgrade head
```

> 資料庫檔案會建立在 `data/autotest.db`

### 6. 建立初始管理員帳號

資料庫初始化後**不會**自動建立任何帳號，需手動執行 seed 腳本：

```powershell
python -m scripts.seed_admin
```

預設帳號密碼如下（可於 `.env` 中設定 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 覆寫）：

| 欄位 | 值 |
|------|-----|
| 帳號 | `admin` |
| 密碼 | `admin` |
| 角色 | `admin`（最高權限）|

> 若該帳號已存在，腳本會印出訊息並跳過，可安全重複執行。
> **建議**：首次登入後請至後台（/admin → 帳號管理）修改預設密碼。
>
> **角色權限**：editor 能上傳並執行 RF 腳本（可執行任意 Python），只給信任的人；viewer 只能查看。Docker 部署下測試在獨立的 runner 容器執行，碰不到金鑰與資料庫；本機開發沒有這層隔離。

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
cd frontend
npm install          # 首次安裝
npm run dev          # 啟動開發伺服器
```

前端運行於：http://localhost:5173

> Vite 已設定 `/api` → `http://localhost:8000` 的反向代理，前後端同時啟動即可正常使用。

---

## 三、執行測試

### 後端測試

```powershell
cd backend
# 確認虛擬環境已啟動

pytest                    # 執行全部測試
pytest tests/unit         # 僅執行 unit tests
pytest tests/contract     # 僅執行 contract tests
pytest tests/integration  # 僅執行 integration tests
pytest -k "test_name"     # 執行特定測試
```

### 前端測試

```powershell
cd frontend
npm run test              # 執行一次（unit tests）
npm run test:watch        # 監看模式

# E2E（Playwright，首次需安裝瀏覽器二進位檔）
npx playwright install
npm run test:e2e          # 需要後端已啟動；前端 dev server 會自動啟動
```

---

## 四、資料庫管理

SQLite 連線一律開啟 WAL 模式（`busy_timeout=5000`、`synchronous=NORMAL`），讓執行中的寫入不會擋住網頁讀取。資料庫旁會多出 `autotest.db-wal`、`autotest.db-shm` 兩個檔案，屬正常現象；備份時請連同它們一起複製，或先停止後端。

```powershell
cd backend

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
.
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
│   │   ├── integration/   # 整合測試
│   │   ├── load/          # 負載測試
│   │   └── performance/   # 效能測試
│   ├── scripts/           # 維運腳本（seed_admin.py 等，需手動執行）
│   ├── libs/              # Robot Framework 自訂 library（CaptchaSolverLibrary 等，驗證碼交給後端 API 辨識）
│   ├── alembic/           # 資料庫 migration
│   ├── data/              # SQLite DB + 媒體檔案（執行時建立）
│   ├── robot_scripts/     # Robot Framework .robot 腳本（執行時產生）
│   ├── .env               # 環境變數（需手動建立）
│   ├── .env.example       # 環境變數範本
│   ├── requirements.txt   # Python 相依套件
│   └── requirements-dev.txt  # 測試相依套件（pytest 等）
│
├── frontend/
│   ├── src/
│   │   ├── components/    # Vue 元件
│   │   ├── pages/         # 頁面元件
│   │   ├── services/      # API 呼叫（axios）
│   │   ├── stores/        # Pinia 狀態管理
│   │   └── router/        # Vue Router 設定
│   ├── tests/
│   │   ├── unit/          # Vitest 單元測試
│   │   └── e2e/           # Playwright E2E 測試
│   └── package.json
│
├── runner/                # runner：接收後端派送的測試並執行（agent.py，Linux 容器與 Windows 主機共用）
├── docs/                  # 部署文件（deploy-oracle.md、windows-runner.md）
├── docker-compose.yml     # frontend / backend / runner 三個服務
└── specs/                 # Spec Kit 規格文件（001 平台、002 RF 上傳、003 執行佇列、004 排程執行）
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
