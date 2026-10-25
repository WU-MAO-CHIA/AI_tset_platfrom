# syntax=docker/dockerfile:1
# AutoTest runner：在獨立容器執行 Robot Framework 測試，容器裡沒有後端的金鑰與資料庫。
FROM node:22-bookworm-slim AS node

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Browser library 以 Node 版 Playwright 驅動瀏覽器
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /opt/runner
COPY requirements.txt .
# rfbrowser init 需要 Chromium 的系統相依套件：借用 Python Playwright 的 install-deps 安裝後移除
RUN pip install -r requirements.txt playwright==1.49.1 \
 && python -m playwright install-deps chromium \
 && rfbrowser init chromium \
 && pip uninstall -y playwright \
 && rm -rf /root/.npm /root/.cache /var/lib/apt/lists/*

COPY agent.py .

# agent 以 root 執行（才能降權、結束整組行程），測試腳本以 runner 使用者執行：
# 讀不到 agent 的環境變數（RUNNER_TOKEN），也沒有後端的任何金鑰或資料。
RUN useradd --create-home --uid 10002 runner
ENV RUNNER_RUN_AS=runner

EXPOSE 9000
HEALTHCHECK --interval=10s --timeout=5s --retries=6 --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=3)"
CMD ["python", "agent.py"]
