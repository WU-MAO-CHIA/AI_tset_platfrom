# Feature Specification: Windows 桌面應用程式測試

**Feature Branch**: `005-windows-desktop-testing`
**Created**: 2026-10-25
**Status**: Approved
**Input**: 「有些應用程式只有 Windows 可以執行」——讓平台除了網頁，也能測試只能在 Windows 上執行的桌面應用程式

## 背景

目前平台只測網頁：AI 產生的腳本固定使用 Browser library（Playwright），執行環境是 Linux 的
`runner` 容器（PR #19）。後端把測試工作打包成 zip，用 HTTP 送給 runner，runner 執行完把結果傳回。

桌面應用程式需要一個**真的 Windows 桌面**：程式要開得起來、要有視窗可以點。Windows 容器沒有桌面，
也不能和現有的 Linux 容器放在同一個 compose，因此 Windows 執行環境是一台 **Windows 電腦或 VM**，
在登入後的桌面裡執行 runner 程式。因為後端與 runner 之間本來就只透過 HTTP 溝通，後端只要能依使用者
在前端選的「執行環境」決定送到哪一台 runner 即可。

執行環境由管理員在前端登記（例如「預設容器」「Windows 測試機 A」，之後也可以再加其他 Linux 容器），
測試人員在案例上選擇預設環境，執行時也可以改選其他環境。

部署不再限定免費平台（2026-10-25），Windows 主機可以是付費的雲端 Windows VM，也可以是公司內的實體電腦。

## User Scenarios & Testing *(mandatory)*

### User Story 0 - 在前端登記與選擇執行環境 (Priority: P1)

管理員在「執行環境」頁登記可用的 runner：名稱、類型（Linux 容器 / Windows）、位址、token。
docker compose 內建的 runner 自動以「預設容器」出現，不能刪除。測試人員在案例編輯頁從下拉選單選執行環境，
選單顯示每個環境的類型與目前是否連線；按「試跑」或執行清單時，對話框也可以改選這次要用的環境。

**Acceptance Scenarios**:

1. **Given** 管理員新增一個 Windows 環境，**When** 儲存，**Then** 平台立即檢查連線並在列表顯示「已連線 / 未連線 / 桌面已鎖定」
2. **Given** 案例編輯頁，**When** 打開執行環境下拉，**Then** 看得到所有啟用中的環境、類型與連線狀態；新案例預設為「預設容器」
3. **Given** 網頁案例，**When** 試跑時改選另一個 Linux 容器，**Then** 這次在該容器執行，案例的預設環境不變
4. **Given** 網頁案例，**When** 試跑時想選 Windows 環境，**Then** 選單不提供（類型不符的環境不能選），反之亦然
5. **Given** viewer 或 editor，**When** 呼叫新增/修改/刪除執行環境 API，**Then** 回 403；token 在任何 API 回應中都不會出現
6. **Given** 執行環境被刪除，**When** 案例原本指向它，**Then** 案例改回同類型的預設環境（Windows 沒有預設時標示「需重新選擇」）

### User Story 1 - 執行手寫的桌面應用程式腳本 (Priority: P1)

測試人員建立一個測試案例，執行環境選一個 Windows 環境，貼上（或上傳）自己寫好的 RF 腳本，按「試跑」，
腳本在 Windows runner 上開啟受測程式、操作畫面並驗證結果，平台顯示和網頁測試相同的結果頁（狀態、log、截圖）。

**Independent Test**: 以 Windows 內建的記事本寫一個案例（開啟、輸入文字、驗證文字、關閉），從平台試跑後得到「通過」，結果頁看得到 log.html 與截圖。

**Acceptance Scenarios**:

1. **Given** 案例的執行環境是 Windows 環境，**When** 試跑，**Then** 工作送到該 Windows runner，不會送到 Linux runner
2. **Given** 執行中腳本失敗，**When** 執行結束，**Then** 結果頁顯示失敗訊息與失敗當下的截圖
3. **Given** 腳本卡住超過逾時時間，**When** 逾時，**Then** runner 結束這次執行啟動的所有程式（含受測程式），狀態為「逾時」，下一個案例不會被殘留的視窗干擾
4. **Given** Windows runner 沒開機或連不到，**When** 執行桌面案例，**Then** 該案例在 30 秒內失敗，訊息為「Windows 執行環境未連線」，網頁案例不受影響

### User Story 2 - 網頁與桌面案例放在同一份清單 (Priority: P1)

測試人員把網頁案例和桌面案例放在同一份回歸清單，按一次執行（或由 spec 004 的排程觸發），
網頁案例照舊在 Linux runner 跑（可平行），桌面案例依序在 Windows runner 跑，最後是同一筆執行記錄、同一份結果。
執行清單的對話框可以把整批網頁案例改到某個 Linux 容器、整批桌面案例改到某個 Windows 環境；不改則各案例用自己的預設環境。

**Acceptance Scenarios**:

1. **Given** 清單有 3 個網頁案例、2 個桌面案例，**When** 執行，**Then** 執行記錄有 5 筆案例結果，各自標示執行環境
2. **Given** 清單開啟平行執行，**When** 執行，**Then** 網頁案例照平行設定執行，桌面案例一律一次一個

### User Story 3 - 登記受測程式並探索視窗元素 (Priority: P2)

管理員在平台登記受測程式（名稱、在 Windows runner 上的執行檔路徑、啟動參數）。測試人員建立桌面案例時
選擇受測程式，按「視窗探索」，平台在 Windows runner 開啟該程式，列出視窗中的按鈕、輸入欄等元素與定位器，
並附上畫面截圖，供撰寫腳本與 AI 產生腳本使用。

**Acceptance Scenarios**:

1. **Given** 已登記記事本，**When** 按「視窗探索」，**Then** 30 秒內看到元素清單（名稱、類型、AutomationId、定位器）與截圖，探索結束後程式被關閉
2. **Given** viewer，**When** 呼叫新增/修改/刪除受測程式 API，**Then** 回 403

### User Story 4 - AI 產生桌面腳本 (Priority: P2)

測試人員輸入桌面案例的步驟，按「產生 RF 程式碼」，AI 依桌面版規則產生腳本：使用桌面自動化函式庫的
keyword、從受測程式設定帶入執行檔路徑、優先沿用視窗探索得到的定位器，沒有根據的定位器標註 TODO。

**Acceptance Scenarios**:

1. **Given** 桌面案例且已做過視窗探索，**When** 產生腳本，**Then** 腳本只使用桌面函式庫與 BuiltIn 的 keyword，不出現 Browser library
2. **Given** 網頁案例，**When** 產生腳本，**Then** 行為與現在完全相同

### Edge Cases

- **Windows 遠端桌面中斷連線**：RDP 斷線後桌面會被鎖定，UI 自動化會失敗。安裝文件必須說明如何讓工作階段留在主控台（不鎖定）並設定自動登入；runner 的 `/health` 回報桌面是否可用。
- **受測程式跳出非預期視窗**（更新提示、授權對話框）：屬於腳本與環境的責任；逾時處理會清掉殘留程式。
- **同一台 Windows 上同時兩個執行**：桌面只有一個，runner 一次只接一個工作，第二個工作回 409，後端排隊等待，不平行。
- **清單只有網頁案例**：行為與現在相同，不會連線 Windows runner。
- **桌面案例被改成網頁案例**（或反過來）：既有腳本保留，但試跑前提示腳本使用的函式庫與執行環境不符。
- **解析度與 DPI**：截圖與座標依 Windows 主機設定；安裝文件建議固定解析度與 100% 縮放。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-000**: 系統 MUST 提供「執行環境」管理頁（admin）：名稱、類型（`linux` / `windows`）、位址、token、啟用狀態；docker compose 的 runner 以「預設容器」內建，不能刪除；token 只能寫入，API 不回傳
- **FR-001**: 測試案例 MUST 有「預設執行環境」欄位，前端以下拉選單選擇；既有與新建案例預設為「預設容器」。案例是網頁或桌面由環境類型決定（`linux` = 網頁、`windows` = 桌面）
- **FR-002**: 試跑與清單執行的對話框 MUST 可以改選這次使用的環境，只列出類型相符、啟用中的環境；改選不影響案例的預設值
- **FR-002a**: 系統 MUST 依選定的環境把工作送到對應的 runner；環境停用、刪除或連不到時給出明確錯誤
- **FR-003**: Windows runner MUST 使用與 Linux runner 相同的 HTTP 介面（`GET /health`、`POST /run`、Bearer token、zip 進 zip 出），後端共用 `runner_client`
- **FR-004**: Windows runner MUST 在逾時或執行結束時結束這次執行啟動的整個程序樹（含受測程式）
- **FR-005**: Windows runner MUST 一次只執行一個工作；忙碌時回 409，後端視為「稍後重試」而非失敗
- **FR-006**: Windows runner 主機 MUST NOT 保存平台的資料庫、JWT 金鑰或 LLM 金鑰；只需要 `RUNNER_TOKEN`
- **FR-007**: 清單執行 MUST 支援混合網頁與桌面案例：網頁案例沿用現有流程（含 pabot 平行），桌面案例依序執行，結果寫入同一筆執行記錄
- **FR-008**: 系統 MUST 提供「受測程式」的管理（名稱、執行檔路徑、啟動參數、主視窗標題），admin 可新增/修改/刪除，所有登入者可讀
- **FR-009**: 系統 MUST 提供視窗探索：在 Windows runner 開啟指定受測程式，回傳元素清單（名稱、控制項類型、AutomationId、定位器）與截圖，結束後關閉程式
- **FR-010**: AI 產生腳本 MUST 依執行環境選擇規則：網頁沿用現有規則；桌面使用桌面函式庫的 keyword 白名單（以 libdoc 驗證存在）與定位器來源規則
- **FR-011**: 執行環境頁與管理儀表板 MUST 顯示每個環境的連線狀態、是否忙碌，Windows 環境另外顯示桌面是否可用
- **FR-012**: 結果頁、清單執行歷史 MUST 顯示每個案例實際使用的執行環境

### Key Entities

- **RunnerEnvironment**（新）：`name`、`kind`（`linux` / `windows`）、`url`、`token`（加密保存）、`enabled`、`is_builtin`、`last_health`、`last_checked_at`
- **TestCase**（既有，擴充）：新增 `runner_environment_id`、`desktop_app_id`（nullable）
- **DesktopApp**（新）：`name`、`executable_path`、`arguments`、`window_title`、`notes`、`created_by`
- **CaseResult**（既有，擴充）：新增 `runner_environment_id` 與 `runner_environment_name`，保留執行當下的環境（環境刪除後仍顯示名稱）

## Success Criteria *(mandatory)*

- **SC-001**: 記事本範例案例從平台試跑，在 Windows runner 上通過，結果頁有 log 與截圖
- **SC-002**: 3 網頁 + 2 桌面的混合清單執行一次，得到 5 筆案例結果，網頁案例的平行設定照常生效
- **SC-003**: 桌面案例逾時後，Windows 主機上沒有殘留這次執行啟動的程式
- **SC-004**: Windows runner 關機時，桌面案例在 30 秒內以明確訊息失敗，網頁案例照常完成
- **SC-005**: 既有後端、前端、runner 測試全部通過；沒有桌面案例時，系統行為與現在相同

## Out of Scope

- Windows 容器（沒有桌面，無法測 GUI）
- 自動挑選空閒環境、負載分配（第一版由使用者選定環境）；同一台 Windows 機器平行執行多個桌面案例
- 自動建立或重設 Windows VM、自動安裝受測程式（由管理員手動安裝與維護）
- 桌面執行過程錄影（第一版只有截圖）
- 桌面版的 AI 自動探索代理（現有網頁 page agent 的桌面版本）
- macOS / Linux 桌面程式、手機 App
- 在 Windows 上執行網頁測試（網頁一律在 Linux runner）

## Decisions

1. **桌面自動化函式庫**：建議 `robotframework-flaui`（以 Microsoft UI Automation 操作 Win32 / WinForms / WPF 程式，持續維護中）。替代方案是 `rpaframework-windows`（RPA.Windows）。第一階段以 libdoc 與記事本範例實測後定案。
2. **Windows 主機**：平台不限定。雲端 Windows VM（例如 Azure、AWS 的 Windows Server）或公司內實體電腦都可以，條件是能開機自動登入、保持桌面不鎖定。
3. **連線方式**：後端與 Windows runner 之間走私有網路（同一雲端的內網，或 WireGuard / Tailscale 這類 VPN），runner 不直接對公網開放。token 驗證照舊。
4. **執行環境在前端登記與選擇**（2026-10-25 使用者要求）：可登記多個 Linux 容器與 Windows 環境；每個 Windows 環境一次一個工作，桌面案例依序執行。
5. **案例有預設環境，執行時可改選**：案例存預設環境，試跑與清單執行可改選同類型的其他環境；網頁或桌面由環境類型決定，不另設欄位。
6. **token 保存方式**：執行環境的 token 以 `JWT_SECRET_KEY` 衍生的金鑰加密存在 DB（`cryptography` 的 Fernet），API 永不回傳；更換 `JWT_SECRET_KEY` 後需重新輸入 token。

第 1–6 點於 2026-10-25 經使用者確認規格後開始實作（第 4、5 點為使用者要求）；第 1 點的函式庫在第二階段實測後定案。
