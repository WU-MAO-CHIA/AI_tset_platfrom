# Implementation Plan: Windows 桌面應用程式測試

**Branch**: `005-windows-desktop-testing` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

新增第二種 runner：在 Windows 電腦（或 VM）的登入桌面上執行的 `runner/agent.py`，介面與 Linux runner
完全相同。後端依案例的 `target_platform` 選擇 runner；清單執行時把案例分成網頁與桌面兩組，網頁照舊，
桌面依序送到 Windows runner。之後再加受測程式登記、視窗探索與 AI 桌面規則。

```
ExecutionWorker
  └─ 清單執行
       ├─ web 案例 ──────────► Linux runner（docker compose，pabot 可平行）
       └─ windows_desktop 案例 ─► Windows runner（Windows 主機登入桌面，一次一個）
                                    └─ robot + robotframework-flaui → 受測程式
```

## Technical Context

**Windows runner**: Python 3.12+（Windows 版）、robotframework、robotframework-flaui（Decision 1）；`agent.py` 只用標準庫
**後端**: 沿用 `src/execution/runner_client.py`，改為接受 runner 位址與 token 參數
**Storage**: SQLite，一個 Alembic migration（兩個欄位 + 一張表）
**Constraints**: Windows runner 不跑在容器裡；一台、一次一個工作；不保存平台機密

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

### `test_cases`（擴充）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `target_platform` | String(20), default `web`, not null | `web` / `windows_desktop` |
| `desktop_app_id` | String(36), nullable | 不加 FK（避免 SQLite batch alter），刪除受測程式時把引用設為 null |

### `case_results`（擴充）

- `target_platform` String(20), nullable：執行當下的環境，之後案例改環境也不影響歷史結果。

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

### 1. 設定

`config.py` 新增 `windows_runner_url: str = ""`、`windows_runner_token: str = ""`；`.env.example`、docker-compose（傳入 backend）、README 補說明。
`RUNNER_TOKEN` 與 `WINDOWS_RUNNER_TOKEN` 加入 `_SENSITIVE_ENV_KEYS`，不傳給測試腳本。

### 2. runner 選擇

- `runner_client.run_remote(workdir, spec, env, *, url, token)`：位址與 token 改由呼叫端傳入；新增 `RunnerBusy`（409）。
- `execution_service._resolve_runner(platform) -> (url, token)`：`web` 依現有 `EXECUTION_RUNNER` 設定；`windows_desktop` 一律走 remote，未設定 `WINDOWS_RUNNER_URL` 時丟出「Windows 執行環境未設定」。
- `RunnerBusy` 時每 5 秒重試，最多等到該案例逾時時間為止。
- 連線逾時設 10 秒，讓 runner 關機時 30 秒內失敗（SC-004）。

### 3. 清單執行

- `_execute_all_cases_bg` 依 `target_platform` 分組：web 組沿用 `_run_sequential` / `_run_pabot`；desktop 組一律走 `_run_sequential`，送到 Windows runner。
- 兩組並行進行（不同機器），各自寫入同一筆 `execution_records` 的 `case_results`，`position` 維持清單順序；SSE 事件不變。
- 試跑 `_execute_trial_bg` 依案例環境選 runner。

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
- `generate_robot_code` / `preview_robot_code` / `chat_and_generate_rf` 依案例 `target_platform` 選擇規則與骨架；網頁路徑 prompt 不變。

## 前端設計

- 案例編輯頁：「執行環境」選擇（網頁 / Windows 桌面）；選桌面時顯示「受測程式」下拉，「頁面探索」按鈕切換成「視窗探索」。
- 切換執行環境時，若既有腳本使用的函式庫不符，顯示提醒。
- 新頁面「受測程式」（admin，Element Plus 表格與表單），導覽列放在管理選單下。
- 結果頁、清單執行歷史：每個案例顯示執行環境標籤。
- 管理儀表板：Windows runner 狀態卡（連線、桌面可用、目前是否忙碌）。

## 測試計畫

**runner（pytest，CI 在 Linux）**
- 既有 14 個測試照跑；平台 hook 以 monkeypatch 模擬 Windows 分支（只允許 robot、全域鎖回 409）
- Job Object 與 FlaUI 相關程式只在 Windows 執行的測試標記 `windows`，CI 加一個 `windows-latest` job 跑 agent 單元測試與記事本範例（GitHub 的 Windows runner 有互動式桌面，可跑 UI 自動化；若實測不穩定，改為只在安裝文件中提供手動驗證步驟）

**後端（pytest）**
- runner 選擇：web / windows_desktop、未設定 Windows runner 的錯誤、409 重試、連線逾時
- 混合清單：以兩個假 runner（測試內啟動 `agent.py`）驗證分組、結果筆數、位置順序、平行設定只影響網頁組
- 受測程式 CRUD 權限、刪除時清除引用、環境變數傳遞
- AI：桌面規則選用、keyword 白名單 libdoc 驗證

**前端（Vitest）**
- 執行環境切換與受測程式下拉、受測程式頁、環境標籤

## 分階段交付（每階段一個 PR）

1. **Windows runner + 執行路由**：agent 跨平台化、`requirements-windows.txt`、`docs/windows-runner.md`、設定、`target_platform` 欄位、runner 選擇、混合清單、前端執行環境選擇與標籤。合併後即可用手寫腳本測桌面程式（US1、US2）。
2. **受測程式 + 視窗探索**：`desktop_apps` 表與 API、`/explore`、前端受測程式頁與視窗探索（US3）。
3. **AI 桌面腳本**：桌面規則、骨架、keyword 白名單、案例頁整合（US4）。
4. **儀表板狀態**：Windows runner 狀態卡（可併入第 2 階段）。

## 風險

- **桌面鎖定**：最常見的失敗原因。以 `/health` 的 `desktop` 欄位提早發現，儀表板顯示，安裝文件明確寫出 RDP 斷線的處理方式。
- **函式庫相容性**：FlaUI 依賴 pythonnet 與 .NET；第一階段先在乾淨的 Windows Server 實測安裝步驟，失敗則改用 Decision 1 的替代方案。
- **CI 無法完整驗證**：Linux CI 無法跑桌面測試；以 `windows-latest` job 補足，最終仍需在實際 Windows runner 上手動驗證一次記事本範例。
- **網路**：Windows runner 與後端不在同一台機器，連線中斷時該批桌面案例會失敗；不做自動重跑，由使用者重新執行。
