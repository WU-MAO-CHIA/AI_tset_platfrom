# syntax=docker/dockerfile:1
# AutoTest 前端：Vite 建置靜態檔，由 nginx 提供並反向代理 /api 到後端
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
# package-lock.json 目前被 .gitignore 排除；有 lock 檔時用 npm ci 鎖定版本
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
