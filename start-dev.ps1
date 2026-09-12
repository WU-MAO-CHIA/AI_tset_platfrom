#!/usr/bin/env pwsh
# 同時啟動前端與後端開發伺服器

$ErrorActionPreference = 'Stop'

$repoRoot = "C:\Users\mark\Desktop\Automatic_Test"
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

Write-Host "=== AutoTest 開發環境啟動腳本 ===" -ForegroundColor Cyan
Write-Host "專案根目錄: $repoRoot"

# 檢查目錄
if (-not (Test-Path $backendDir)) {
    Write-Error "找不到後端目錄: $backendDir"
    exit 1
}
if (-not (Test-Path $frontendDir)) {
    Write-Error "找不到前端目錄: $frontendDir"
    exit 1
}

# 啟動後端
Write-Host "`n[1/2] 啟動後端 (FastAPI + Uvicorn)..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendDir'; `$env:PYTHONPATH='.'; .\.venv\Scripts\Activate.ps1; python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
) -PassThru

# 等待後端啟動
Write-Host "等待後端啟動 (3 秒)..."
Start-Sleep -Seconds 3

# 啟動前端
Write-Host "`n[2/2] 啟動前端 (Vite)..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; npm run dev"
) -PassThru

Write-Host "`n=== 開發環境已啟動 ===" -ForegroundColor Cyan
Write-Host "後端 API:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "前端頁面:  http://localhost:5173" -ForegroundColor Yellow
Write-Host "API 文件:   http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "按 Ctrl+C 可關閉此視窗（但子進程會繼續在獨立視窗運行）" -ForegroundColor Gray