# Quickstart: 自動化測試平台

**Phase**: 1 | **Date**: 2026-05-19 | **Plan**: [plan.md](./plan.md)

## Prerequisites

- Python 3.14
- Node.js 20+
- Git

## 1. 環境設定

```bash
# Clone repo
git clone <repo-url>
cd AI_Auto_test/automatic_test

# Backend 依賴
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend 依賴
cd ../frontend
npm install
```

## 2. 設定檔

複製範例設定並填入：

```bash
cp backend/.env.example backend/.env
```

```dotenv
# backend/.env
DATABASE_URL=sqlite:///./data/autotest.db
MEDIA_ROOT=./data/media
ROBOT_SCRIPTS_DIR=./robot_scripts
PARALLEL_MAX_WORKERS=5

# LLM API 金鑰（至少設定一個）
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# 預設使用的 LLM 模型
DEFAULT_LLM_MODEL=claude-3-5-sonnet
```

## 3. 資料庫初始化

```bash
cd backend
alembic upgrade head
```

## 4. 啟動服務

```bash
# Backend（開發模式）
cd backend
uvicorn src.main:app --reload --port 8000

# Frontend（開發模式，另開 terminal）
cd frontend
npm run dev
```

訪問 `http://localhost:5173` 開始使用。

## 5. 執行測試

```bash
# Backend 全部測試（TDD 驗證）
cd backend
pytest

# Backend 只跑 unit tests
pytest tests/unit/

# Backend 只跑 integration tests（需要 DB）
pytest tests/integration/

# Frontend 測試
cd frontend
npm run test

# Frontend e2e（需要後端運行中）
npm run test:e2e
```

## 6. 快速功能驗證

### 建立第一個測試案例
```bash
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "TC-001",
    "name": "示範登入測試",
    "main_steps": "1. 開啟 https://example.com\n2. 點擊登入按鈕\n3. 輸入帳號密碼\n4. 確認登入成功",
    "system_category": "auth",
    "created_by": "admin"
  }'
```

### 執行 AI 步驟補齊
```bash
curl -X POST http://localhost:8000/api/v1/cases/TC-001-UUID/ai-complete \
  -H "Content-Type: application/json" \
  -d '{
    "partial_steps": "1. 開啟登入頁面",
    "llm_model": "claude-3-5-sonnet"
  }'
```

### 建立清單並執行
```bash
# 建立清單
curl -X POST http://localhost:8000/api/v1/checklists \
  -H "Content-Type: application/json" \
  -d '{"name": "Sprint 1 測試", "created_by": "admin", "case_ids": ["TC-001-UUID"]}'

# 執行清單
curl -X POST http://localhost:8000/api/v1/checklists/CL-001-UUID/execute \
  -H "Content-Type: application/json" \
  -d '{"executed_by": "admin", "parallel_mode": false}'
```

## 7. 開發流程（TDD）

1. 根據 `specs/001-auto-test-platform/tasks.md` 選取任務
2. 閱讀對應的 FR 規格（spec.md）
3. 先寫 failing test（`pytest` 確認 RED）
4. 實作最小可行代碼（`pytest` 確認 GREEN）
5. Refactor（保持 GREEN）
6. Commit：`[Spec Kit] 實作 FR-xxx: {描述}`

## 8. 目錄結構快速參考

```
automatic_test/
├── backend/
│   ├── src/
│   │   ├── models/          # SQLAlchemy 資料模型
│   │   ├── repositories/    # DB CRUD
│   │   ├── services/        # 業務邏輯
│   │   ├── api/             # FastAPI 路由
│   │   └── core/            # 設定、DB engine
│   └── tests/               # pytest
├── frontend/
│   ├── src/
│   │   ├── components/      # Vue 元件
│   │   ├── pages/           # 路由頁面
│   │   ├── services/        # API client
│   │   └── stores/          # Pinia 狀態
│   └── tests/               # Vitest
├── robot_scripts/
│   ├── generated/           # AI 生成的 .robot 檔
│   └── results/             # RF 執行輸出
└── specs/
    └── 001-auto-test-platform/   # 本計劃文件
```
