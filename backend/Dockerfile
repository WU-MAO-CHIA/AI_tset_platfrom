# syntax=docker/dockerfile:1
# AutoTest 後端：FastAPI + Robot Framework（Browser library）+ Playwright
FROM node:22-bookworm-slim AS node

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Browser library 以 Node 版 Playwright 驅動瀏覽器：執行期需要 node，建置期另需 npm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /app

COPY requirements.txt .
# 兩套 Playwright 各自需要對應版本的 chromium：
#   - Python Playwright（頁面探索）：playwright install，--with-deps 一併安裝系統相依套件
#   - Node Playwright（Browser library 執行 RF 腳本）：rfbrowser init
RUN pip install -r requirements.txt \
 && python -m playwright install --with-deps chromium \
 && rfbrowser init chromium \
 && rm -rf /root/.npm /root/.cache /var/lib/apt/lists/*

COPY . .

RUN useradd --create-home --uid 10001 app \
 && mkdir -p data/media data/execution_reports robot_scripts \
 && chown -R app:app data robot_scripts
USER app

EXPOSE 8000

# 啟動前套用 migration（alembic.ini 固定使用 ./data/autotest.db）並建立初始 admin（已存在則略過）。
# 只能跑單一 worker：執行佇列與頁面探索 session 存在 process 記憶體中。
# 只經由 frontend 的 nginx 存取，故信任其 X-Forwarded-For（登入限流才能依實際 client IP 計算）。
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_admin && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
