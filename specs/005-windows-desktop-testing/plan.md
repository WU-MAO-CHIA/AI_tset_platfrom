# Implementation Plan: Windows 桌面應用程式測試

**Branch**: `005-windows-desktop-testing` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

新增第二種 runner：在 Windows 電腦（或 VM）的登入桌面上執行的 `runner/agent.py`，介面與 Linux runner
完全相同。執行環境（runner 清單）存在 DB，由 admin 在前端登記；案例有預設環境，試跑與清單執行時可改選。
後端依選定環境送出工作；清單執行時依環境分組，網頁照舊，桌面依序送到 Windows runner。
之後再加受測程式登記、視窗探索與 AI 桌面規則。

```
ExecutionWorker
  └─ 清單執行
       ├─ 網頁案例（linux 環境）──► 預設容器或其他 Linux runner（pabot 可平行）
       └─ 桌面案例（windows 環境）► 選定的 Windows runner（Windows 主機登入桌面，一次一個）
                                    └─ robot + robotframework-flaui → 受測程式
```

## Technical Context

**Windows runner**: Python 3.12+（Windows 版）、robotframework、robotframework-flaui（Decision 1）；`agent.py` 只用標準庫
**後端**: 沿用 `src/execution/runner_client.py`，改為接受 runner 位址與 token 參數
**Storage**: SQLite，每階段各一個 Alembic migration（`runner_environments`、`desktop_apps` 兩張表與既有表的新欄位）；token 加密用既有的 `cryptography`
**Constraints**: Windows runner 不跑在容器裡；每個 Windows 環境一次一個工作；runner 主機不保存平台機密

## Windows runner

### `runner/agent.py` 跨平台化

目前 agent 用了只有 Linux 才有的功能，Windows 版改法：

| 功能 | Linux（現況） | Windows |
|---|---|---|
| 降權 | root 啟動，`Popen(user=runner)` | 不切換使用者；agent 本身以自動登入的一般帳號執行 |
| 逾時結束整組程式 | `start_new_session` + `os.killpg` | 把子程序放進 Job Object（`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`，ctypes 呼叫），逾時或結束時關閉 job；退路 `taskkill /F /T /PID` |
| 工具 | robot、pabot | 只允許 robot（桌面無法平行） |
| 同時執行 | 不限 | 全域鎖，忙碌回 409 |
| `/health` | `{"ok": true}` | 加上 `desktop`：是否有互動式桌面、是否鎖定（`OpenInputDesktop` 檢查） |

平台判斷集中在一個 `_platform_hooks()`，Linux 路徑行為不變，既有 14 個 runner 測試照跑。

### 安裝與部署（`docs/windows-runner.md`）

- 安裝 Python、`pip install -r runner/requirements-windows.txt`
- 建立專用的本機一般帳號，設定開機自動登入（Sysinternals Autologon），停用螢幕保護與自動鎖定
- 以「工作排程器：登入時執行」啟動 agent（不能做成 Windows 服務，服務在 session 0 看不到桌面）
- 用遠端桌面維護時，離開前以 `tscon` 把工作階段交回主控台，避免桌面鎖定
- 固定解析度（例如 1920×1080）與 100% 縮放
- 防火牆只允許私有網路連到 agent 埠（Decision 3）；`RUNNER_TOKEN` 至少 32 字元
- 受測程式由管理員手動安裝

## 資料模型（一個 Alembic migration）

### `runner_environments`（新）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | String(36) PK | uuid；內建環境固定 id `builtin-linux` |
| `name` | String(100), unique | 例如「預設容器」「Windows 測試機 A」 |
| `kind` | String(20) | `linux` / `windows` |
| `url` | String(500) | 內建環境為空，執行時讀 `RUNNER_URL` |
| `token_encrypted` | Text, nullable | Fernet 加密（金鑰由 `JWT_SECRET_KEY` 以 HKDF 衍生）；內建環境為空，讀 `RUNNER_TOKEN` |
| `enabled` | Boolean, default true | |
| `is_builtin` | Boolean, default false | 不能刪除、不能改類型 |
| `last_health` | JSON, nullable | 最近一次 `/health` 結果（連線、忙碌、桌面狀態） |
| `last_checked_at` | DateTime(tz), nullable | |
| `created_at` / `updated_at` | TimestampMixin | |

migration 建表時寫入內建環境一筆。`EXECUTION_RUNNER=local`（本機開發）時，內建環境代表後端自己執行。

### `test_cases`（擴充）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `runner_environment_id` | String(36), default `builtin-linux`, not null | 既有案例全部指向內建環境；不加 FK（避免 SQLite batch alter），刪除環境時由服務層改寫引用 |
| `desktop_app_id` | String(36), nullable | 不加 FK，刪除受測程式時把引用設為 null |

案例是網頁或桌面由環境的 `kind` 決定（`platform_of(case)`），不另存欄位。

### `case_results`（擴充）

- `runner_environment_id` String(36), nullable、`runner_environment_name` String(100), nullable：執行當下的環境，之後案例改環境或環境被刪除也不影響歷史結果。

### `desktop_apps`（新）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | String(36) PK | uuid |
| `name` | String(100), unique | |
| `executable_path` | String(500) | Windows runner 上的路徑，例如 `C:\Windows\System32\notepad.exe` |
| `arguments` | String(500), nullable | |
| `window_title` | String(200), nullable | 主視窗標題，用於 attach 與探索 |
| `notes` | Text, nullable | |
| `created_by` | String(100) | |
| `created_at` / `updated_at` | TimestampMixin | |

## 後端設計

### 1. 執行環境 API（`src/api/runner_environments.py`）

| Method | Path | 權限 |
|---|---|---|
| GET | `/runner-environments` | 登入即可；回傳名稱、類型、啟用、最近狀態，不含 url 與 token（admin 另含 url） |
| POST | `/runner-environments` | admin；儲存後立即呼叫一次 `/health` |
| PUT | `/runner-environments/{id}` | admin；token 欄位留空表示不變 |
| DELETE | `/runner-environments/{id}` | admin；內建環境 400；引用的 linux 案例改回內建環境，windows 案例設為「需重新選擇」（指向 null 並在前端提示） |
| POST | `/runner-environments/{id}/check` | editor+；立即重新檢查連線 |

- 背景每 60 秒檢查所有啟用中的環境，更新 `last_health`（與 `ScheduleRunner` 同樣在 startup 開啟的 asyncio task）。
- url 驗證：只允許 `http` / `https`；這是 admin 才能設定的值，不做 SSRF 阻擋，但不回傳 `/health` 以外的內容。

### 2. runner 選擇

- `runner_client.run_remote(workdir, spec, env, *, url, token)`：位址與 token 改由呼叫端傳入；新增 `RunnerBusy`（409）。
- `execution_service._resolve_runner(environment_id) -> RunnerTarget(url, token, kind, name)`：內建環境依現有 `EXECUTION_RUNNER` / `RUNNER_URL` / `RUNNER_TOKEN`；其他環境解密 token 後走 remote；停用或不存在時丟出明確錯誤。
- `RUNNER_TOKEN` 已在 `_SENSITIVE_ENV_KEYS`；解密後的環境 token 只放在 HTTP header，不進入測試腳本環境變數。
- `RunnerBusy` 時每 5 秒重試，最多等到該案例逾時時間為止。
- 連線逾時設 10 秒，讓 runner 關機時 30 秒內失敗（SC-004）。

### 3. 清單執行

- 執行 API（試跑、清單執行、spec 004 排程）新增選填參數 `linux_environment_id`、`windows_environment_id`：有值時整批同類型案例改用該環境，沒有則用各案例的預設環境；類型不符回 400。排程也可以存這兩個欄位（`execution_schedules` 加兩個 nullable 欄位）。
- `_execute_all_cases_bg` 依實際環境分組：每個 linux 環境一組，沿用 `_run_sequential` / `_run_pabot`；每個 windows 環境一組，一律 `_run_sequential`。
- 各組並行進行（不同機器），寫入同一筆 `execution_records` 的 `case_results`，`position` 維持清單順序；SSE 事件不變。
- 試跑 `_execute_trial_bg` 依選定環境送出。

### 4. 受測程式 API（`src/api/desktop_apps.py`）

| Method | Path | 權限 |
|---|---|---|
| GET | `/desktop-apps` | 登入即可 |
| POST | `/desktop-apps` | admin |
| PUT | `/desktop-apps/{id}` | admin |
| DELETE | `/desktop-apps/{id}` | admin；引用的案例 `desktop_app_id` 設為 null |

執行時把選定程式的 `executable_path`、`arguments`、`window_title` 以 `APP_PATH`、`APP_ARGS`、`APP_WINDOW_TITLE` 環境變數傳給腳本（腳本以 `%{APP_PATH}` 讀取），腳本不必寫死路徑。

### 5. 視窗探索

- Windows runner 新增 `POST /explore`（同一個 token、同一個全域鎖）：body `{executable_path, arguments, window_title, timeout}`，
  啟動程式、等待主視窗，以 FlaUI 走訪 UI Automation 樹（深度與數量上限），回傳元素清單 `{name, control_type, automation_id, xpath}` 與 PNG 截圖（base64），最後關閉 job。
- 後端 `POST /cases/explore-window`（editor+）轉送並把結果存成與網頁探索相同的元素目錄，供 AI 產生腳本的「KNOWN PAGE ELEMENTS」區塊使用。

### 6. AI 產生腳本

- `ai_service.py` 新增 `_RF_RULES_DESKTOP` 與 `_DESKTOP_SCRIPT_SKELETON`：`Library    FlaUILibrary`、Test Setup 以 `%{APP_PATH}` 啟動程式、Teardown 關閉程式、定位器只能來自探索結果或使用者提供、沒有根據標 `# TODO: locator 未驗證`、斷言規則。
- keyword 白名單 `_DESKTOP_KEYWORDS` 以 libdoc 測試驗證存在（與現有 `test_ai_service_rf_rules.py` 相同做法；CI 在 Linux 上只做 libdoc 文件檢查，不實際操作視窗）。
- `generate_robot_code` / `preview_robot_code` / `chat_and_generate_rf` 依案例的平台（環境類型）選擇規則與骨架；網頁路徑 prompt 不變。

## 前端設計

- 新頁面「執行環境」（admin，Element Plus 表格與表單）：名稱、類型、位址、token（密碼欄，編輯時留空表示不變）、啟用開關、連線狀態標籤（已連線 / 未連線 / 忙碌 / 桌面已鎖定）、「重新檢查」按鈕。
- 共用元件 `RunnerEnvironmentSelect`：下拉選單，每個選項顯示名稱、類型圖示與連線狀態，可依類型過濾。
- 案例編輯頁：「執行環境」下拉（`RunnerEnvironmentSelect`）；選到 Windows 環境時顯示「受測程式」下拉，「頁面探索」按鈕切換成「視窗探索」。
- 試跑：按鈕旁顯示目前環境，可展開改選同類型的其他環境。
- 清單執行對話框、排程表單：「網頁案例的環境」「桌面案例的環境」兩個選填下拉，預設「依各案例設定」；清單裡沒有該類型案例時隱藏。
- 切換執行環境類型時，若既有腳本使用的函式庫不符，顯示提醒。
- 新頁面「受測程式」（admin，Element Plus 表格與表單），導覽列放在管理選單下。
- 結果頁、清單執行歷史：每個案例顯示執行環境標籤。
- 管理儀表板：各執行環境的狀態卡（連線、目前是否忙碌、Windows 桌面是否可用）。

## 測試計畫

**runner（pytest，CI 在 Linux）**
- 既有 14 個測試照跑；平台 hook 以 monkeypatch 模擬 Windows 分支（只允許 robot、全域鎖回 409）
- Job Object 與 FlaUI 相關程式只在 Windows 執行的測試標記 `windows`，CI 加一個 `windows-latest` job 跑 agent 單元測試與記事本範例（GitHub 的 Windows runner 有互動式桌面，可跑 UI 自動化；若實測不穩定，改為只在安裝文件中提供手動驗證步驟）

**後端（pytest）**
- 執行環境 CRUD 權限、token 不出現在任何回應、加解密、內建環境不能刪、刪除時改寫案例引用、健康檢查更新狀態
- runner 選擇：內建 / 自訂 linux / windows、執行時改選、類型不符 400、停用環境錯誤、409 重試、連線逾時
- 混合清單：以兩個假 runner（測試內啟動 `agent.py`）驗證分組、結果筆數、位置順序、平行設定只影響網頁組
- 受測程式 CRUD 權限、刪除時清除引用、環境變數傳遞
- AI：桌面規則選用、keyword 白名單 libdoc 驗證

**前端（Vitest）**
- 執行環境頁（token 欄位行為、狀態標籤）、`RunnerEnvironmentSelect` 類型過濾、試跑與清單執行改選環境、受測程式下拉、受測程式頁、環境標籤

## 分階段交付（每階段一個 PR）

1. **執行環境管理 + 前端選擇**：`runner_environments` 表與 API、健康檢查、案例預設環境、執行時改選、前端執行環境頁與下拉選單。只用 Linux 環境也能獨立使用（例如多加一個 Linux 容器）（US0）。
2. **Windows runner**：agent 跨平台化、`requirements-windows.txt`、`docs/windows-runner.md`、混合清單分組。合併後即可用手寫腳本測桌面程式（US1、US2）。
3. **受測程式 + 視窗探索**：`desktop_apps` 表與 API、`/explore`、前端受測程式頁與視窗探索（US3）。
4. **AI 桌面腳本**：桌面規則、骨架、keyword 白名單、案例頁整合（US4）。
5. **儀表板狀態**：各執行環境狀態卡（可併入第 1 階段）。

## 風險

- **桌面鎖定**：最常見的失敗原因。以 `/health` 的 `desktop` 欄位提早發現，儀表板顯示，安裝文件明確寫出 RDP 斷線的處理方式。
- **函式庫相容性**：FlaUI 依賴 pythonnet 與 .NET；第一階段先在乾淨的 Windows Server 實測安裝步驟，失敗則改用 Decision 1 的替代方案。
- **CI 無法完整驗證**：Linux CI 無法跑桌面測試；以 `windows-latest` job 補足，最終仍需在實際 Windows runner 上手動驗證一次記事本範例。
- **網路**：Windows runner 與後端不在同一台機器，連線中斷時該批桌面案例會失敗；不做自動重跑，由使用者重新執行。
