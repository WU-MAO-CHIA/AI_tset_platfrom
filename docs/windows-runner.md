# Windows runner 安裝說明

有些受測程式只能在 Windows 桌面執行。平台把這類測試送到一台 **Windows 電腦（實體機或雲端 VM）**，
由同一支 `runner/agent.py` 接收、用 Robot Framework + [FlaUI](https://github.com/GDATASoftwareAG/robotframework-flaui)
操作桌面程式，再把報告傳回平台。

> Windows 容器沒有桌面，不能跑 UI 自動化，所以 Windows runner **不使用 Docker**。

## 運作方式與限制

- 平台後端以 HTTP 呼叫 runner（預設埠 9000），用 `RUNNER_TOKEN` 驗證。runner 主機上不放任何平台金鑰或資料庫。
- 一台 Windows runner **一次只跑一個工作**（只有一個桌面）。忙碌時回 409，平台每 5 秒重送，最多等 10 分鐘。
- 只接受 `robot`（不平行執行）。
- 每個工作結束或逾時，runner 會結束 robot 與它開啟的所有程式（Job Object，失敗時用 `taskkill /T /F`）。
  受測程式若是交給「已在執行的單一實例程式」開啟，runner 抓不到，請在腳本的 Teardown 自行關閉。
- runner 以登入桌面的那個 Windows 帳號執行，**不會切換成低權限使用者**。這台電腦請只拿來跑測試，
  不要登入個人帳號或存放其他資料；能編輯測試腳本的人等同可以在這台電腦上執行程式。

## 1. 準備 Windows 電腦

- Windows 10 / 11 或 Windows Server 2019 以上（要有桌面體驗）。
- 建立專用的**本機一般帳號**，例如 `autotest`（不要用系統管理員帳號跑 runner）。
- 以系統管理員手動安裝受測程式。

## 2. 安裝 Python 與 runner

以 `autotest` 帳號登入後，在 PowerShell 執行：

```powershell
winget install -e --id Python.Python.3.13
# 重新開一個 PowerShell 讓 PATH 生效
mkdir C:\autotest-runner
cd C:\autotest-runner
# 從專案複製 runner\agent.py、runner\requirements-windows.txt、runner\examples\ 到這個資料夾
py -3.13 -m venv .venv
.\.venv\Scripts\pip install -r requirements-windows.txt
```

先在本機確認 FlaUI 能操作桌面（會開啟記事本再關閉）：

```powershell
.\.venv\Scripts\python -m robot --outputdir $env:TEMP\notepad-check examples\notepad.robot
```

## 3. 設定 token 與啟動腳本

產生至少 32 字元的 token（之後要填進平台的「執行環境」頁）：

```powershell
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

建立 `C:\autotest-runner\start-runner.cmd`：

```bat
@echo off
cd /d C:\autotest-runner
set RUNNER_TOKEN=請貼上剛才產生的 token
set RUNNER_PORT=9000
.venv\Scripts\python agent.py >> runner.log 2>&1
```

這個檔案含 token，請確認只有 `autotest` 與系統管理員能讀取：

```powershell
icacls C:\autotest-runner\start-runner.cmd /inheritance:r /grant:r "autotest:(R)" "Administrators:(F)"
```

## 4. 開機自動登入、登入時啟動 runner

UI 自動化需要**已登入且未鎖定的桌面**。runner 不能做成 Windows 服務（服務在 session 0，看不到桌面）。

1. **自動登入**：用 Microsoft 的 [Sysinternals Autologon](https://learn.microsoft.com/sysinternals/downloads/autologon)
   設定 `autotest` 帳號開機自動登入（密碼會以 LSA 加密保存）。
2. **停用自動鎖定**：設定 → 個人化 → 鎖定畫面 → 螢幕保護程式設為「無」；電源選項 → 螢幕與睡眠都設為「永不」。
3. **登入時啟動 runner**：以系統管理員開 PowerShell：

   ```powershell
   $action  = New-ScheduledTaskAction -Execute "C:\autotest-runner\start-runner.cmd"
   $trigger = New-ScheduledTaskTrigger -AtLogOn -User "autotest"
   $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
   Register-ScheduledTask -TaskName "AutoTest Runner" -Action $action -Trigger $trigger -Settings $settings `
     -User "autotest" -RunLevel Limited
   ```

   工作要設定成「只在使用者登入時執行」（上面的指令預設如此），程式才會在 `autotest` 的桌面上。
4. **固定解析度與縮放**：建議 1920×1080、縮放 100%。解析度或縮放改變時，座標點擊與截圖都可能不同。

重新開機確認：電腦自動登入 `autotest`，工作管理員裡有 `python.exe`，`C:\autotest-runner\runner.log` 出現
`runner listening on :9000 (windows desktop, one job at a time)`。

## 5. 防火牆

只允許平台後端所在的網路連到 9000 埠，不要對網際網路開放：

```powershell
New-NetFirewallRule -DisplayName "AutoTest Runner" -Direction Inbound -Protocol TCP -LocalPort 9000 `
  -RemoteAddress 10.0.0.0/8 -Profile Private,Domain -Action Allow
```

`-RemoteAddress` 改成平台後端的 IP 或網段。平台與 runner 不在同一個內網時，請用 VPN（例如 WireGuard、Tailscale）連起來，
不要直接把 9000 埠開到公網：runner 走 HTTP，token 會以明文傳送。

## 6. 在平台登記

以管理員登入平台 → 上方選單「執行環境」→「新增環境」：

- 類型：**Windows（桌面程式）**
- 位址：`http://<Windows 電腦的 IP>:9000`
- Token：第 3 步產生的 token

儲存後狀態應顯示「已連線」。其他狀態：

| 狀態 | 意思 | 處理 |
|---|---|---|
| 未連線 | 連不到 runner | 確認 runner 有在執行、防火牆、IP |
| token 錯誤 | token 與 runner 的 `RUNNER_TOKEN` 不同 | 編輯環境重新貼上 token |
| 桌面已鎖定 | Windows 在鎖定畫面，或遠端桌面斷線後桌面被鎖 | 見下方「用遠端桌面維護」 |
| 執行中 | 正在跑工作 | 其他工作會排隊等候 |

接著在測試案例的「執行環境」選這台 Windows，案例就會送到這裡執行。

## 用遠端桌面維護

用遠端桌面（RDP）連進去後**直接關掉視窗**，主控台工作階段會被鎖定，之後的測試都會失敗。
維護完畢請改用下面的指令離開，把工作階段交回主控台（桌面保持解鎖）：

```powershell
# 以系統管理員執行；會中斷你的遠端桌面連線
$id = (Get-Process -Id $PID).SessionId
tscon $id /dest:console
```

可以把這兩行存成桌面上的 `disconnect-to-console.ps1`，維護完以系統管理員身分執行。

雲端 VM 若只能用 RDP 連線、主控台沒有實體螢幕，tscon 之後的桌面解析度會變成主控台預設值（通常 1024×768）；
需要固定解析度時請在雲端主控台調整，或安裝虛擬顯示驅動程式。

## 撰寫桌面測試

腳本使用 `FlaUILibrary`，元素以 XPath 指定（工具：Windows SDK 的 Accessibility Insights 或 FlaUInspect 可以看元素樹）：

```robotframework
*** Settings ***
Library    FlaUILibrary

*** Test Cases ***
Login Button Works
    Launch Application    C:\\Program Files\\MyApp\\MyApp.exe
    Wait Until Element Exist    /Window[@Name='MyApp']
    Click    /Window[@Name='MyApp']//Button[@Name='登入']
    [Teardown]    Close Application By Name    MyApp
```

完整範例見 `runner/examples/notepad.robot`。關鍵字說明：
<https://gdatasoftwareag.github.io/robotframework-flaui/keywords/latest.html>

## 更新 runner

覆蓋 `agent.py` 與 `requirements-windows.txt` 後執行 `.\.venv\Scripts\pip install -r requirements-windows.txt`，
再到工作排程器把「AutoTest Runner」結束並重新執行（或重新開機）。
