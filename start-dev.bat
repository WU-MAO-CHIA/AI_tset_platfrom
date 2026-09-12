@echo off
REM AutoTest 開發環境啟動腳本 (批次檔版本)
REM 雙擊即可同時啟動前後端

chcp 65001 >nul
title AutoTest 開發環境

set REPO_ROOT=C:\Users\mark\Desktop\Automatic_Test
set BACKEND_DIR=%REPO_ROOT%\backend
set FRONTEND_DIR=%REPO_ROOT%\frontend

echo =========================================
echo   AutoTest 開發環境啟動中...
echo =========================================
echo.

echo [1/2] 啟動後端 (FastAPI)...
start "AutoTest Backend" cmd /k "cd /d %BACKEND_DIR% && .venv\Scripts\activate.bat && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] 啟動前端 (Vite)...
start "AutoTest Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo =========================================
echo   開發環境已啟動
echo =========================================
echo 後端 API:  http://localhost:8000
echo 前端頁面:  http://localhost:5173
echo API 文件:  http://localhost:8000/docs
echo.
echo 關閉這些視窗即可停止服務
echo =========================================
pause