#!/usr/bin/env pwsh
# 同時啟動前後端（同一終端機，使用背景作業）

$ErrorActionPreference = 'Stop'

$repoRoot = "C:\Users\mark\Desktop\Automatic_Test"
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

Write-Host "=== AutoTest 開發環境啟動腳本 (背景作業模式) ===" -ForegroundColor Cyan

# 啟動後端背景作業
$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    .\.venv\Scripts\Activate.ps1
    python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
} -ArgumentList $backendDir

# 啟動前端背景作業
$frontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev
} -ArgumentList $frontendDir

Write-Host "後端啟動中... (Job ID: $($backendJob.Id))" -ForegroundColor Green
Write-Host "前端啟動中... (Job ID: $($frontendJob.Id))" -ForegroundColor Green

# 等待一下讓服務啟動
Start-Sleep -Seconds 5

# 顯示狀態
Write-Host "`n=== 服務狀態 ===" -ForegroundColor Cyan
Get-Job | Format-Table Id, State, HasMoreData, Location, Command -AutoSize

Write-Host "`n=== 存取網址 ===" -ForegroundColor Cyan
Write-Host "後端 API:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "前端頁面:  http://localhost:5173" -ForegroundColor Yellow
Write-Host "API 文件:   http://localhost:8000/docs" -ForegroundColor Yellow

Write-Host "`n按 Enter 停止所有服務並退出..." -ForegroundColor Gray
Read-Host

# 清理作業
Write-Host "`n正在停止服務..." -ForegroundColor Red
Get-Job | Stop-Job
Get-Job | Remove-Job
Write-Host "已停止所有背景作業。" -ForegroundColor Green