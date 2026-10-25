# 部署到 Oracle Cloud Always Free（Ampere A1）

以 Oracle Cloud 永久免費的 ARM VM 執行整套平台：主機上跑 `docker compose`，前面加一層 Caddy 提供 HTTPS。

```
瀏覽器 ──HTTPS──▶ Caddy（主機 :443） ──▶ frontend nginx（127.0.0.1:8080） ──/api──▶ backend
```

> `APP_ENV=prod` 的登入 cookie 帶 `Secure`，必須經由 HTTPS 存取，測試執行的即時進度才會顯示，所以這份指南一定會設定 HTTPS。

## 1. 建立 Oracle Cloud 帳號

- 註冊時需要信用卡驗證（只做小額預授權，不會扣款）。
- **Home region 選了就不能改**，Always Free 資源只能開在 home region。台灣使用者建議選 `Japan East (Tokyo)`、`Japan Central (Osaka)` 或 `Singapore`。
- 建議之後把帳號升級成 **Pay As You Go**：只要資源維持在 Always Free 額度內就不會收費，但比較容易開到 A1 機器，也不會因閒置被回收。升級後記得到 Billing 設定預算警示（例如 1 美元）。

## 2. 建立 VM

Compute → Instances → Create instance：

| 項目 | 設定 |
|------|------|
| Image | Canonical Ubuntu 24.04（aarch64） |
| Shape | `VM.Standard.A1.Flex`，4 OCPU、24 GB RAM（開不到時先試 2 OCPU / 12 GB） |
| Boot volume | 100 GB（Always Free 區塊儲存總額 200 GB） |
| Networking | 新建 VCN 與 public subnet，勾選指派 public IPv4 |
| SSH keys | 上傳自己的公鑰 |

出現 `Out of capacity` 時，換一個 Availability Domain 或過一段時間再試。

### 開放 80 / 443

需要改兩個地方，少一個都連不進來：

1. **Security List**：VCN → Subnet → Security List → Add Ingress Rules，來源 `0.0.0.0/0`，TCP 目的 port `80` 與 `443`。
2. **VM 內的 iptables**：Oracle 的 Ubuntu 映像檔預設只放行 22 port。

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 3. 安裝 Docker

```bash
ssh ubuntu@<VM 公開 IP>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit   # 重新登入讓 docker 群組生效
```

重新登入後確認：`docker compose version`。

### 擋住容器連到雲端元資料服務

測試腳本能執行任意程式，不要讓它從容器裡連到 Oracle 的元資料服務 `169.254.169.254`（可查到 VM 的身分資訊）。
`DOCKER-USER` 只影響容器的流量，VM 本身照常可用：

```bash
sudo iptables -I DOCKER-USER -d 169.254.169.254 -j DROP
sudo netfilter-persistent save
```

## 4. 下載專案並設定

```bash
git clone https://github.com/WU-MAO-CHIA/AI_tset_platfrom.git
cd AI_tset_platfrom
cp backend/.env.example backend/.env
openssl rand -hex 32   # 產生 JWT_SECRET_KEY 用的隨機字串
nano backend/.env
```

正式環境需要改的欄位：

| 欄位 | 值 |
|------|------|
| `APP_ENV` | `prod` |
| `JWT_SECRET_KEY` | 上面 `openssl` 產生的字串（`prod` 拒絕範例檔的值） |
| `ADMIN_PASSWORD` | 強密碼（`prod` 拒絕預設的 `admin`） |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | 至少一組 |
| `JWT_EXPIRE_MINUTES` | 閒置逾時（分鐘，整數）；範例檔為 `10`，有操作就自動續期，閒置超過才需重新登入 |
| `OLLAMA_BASE_URL` | 留空（VM 上沒有 Ollama） |

讓前端只聽本機，對外一律經過 Caddy：

```bash
echo 'FRONTEND_PORT=127.0.0.1:8080' > .env
```

（專案根目錄的 `.env` 由 docker compose 讀取，和 `backend/.env` 是不同的檔案。）

> **帳號角色注意**：editor 可以上傳並執行 Robot Framework 腳本，而 RF 腳本能執行任意 Python。
> 後端容器以另一個使用者 `runner` 執行測試，讀不到 JWT / LLM 金鑰與資料庫，也改不到其他人的腳本；
> 但它仍在同一個容器、可以上網，所以 editor 還是只給信任的人，其他人用 viewer（只能看結果，不能執行或呼叫 AI）。

## 5. 建置並啟動

```bash
docker compose up -d --build
docker compose ps        # backend 應顯示 healthy
curl -I http://127.0.0.1:8080
```

ARM 主機第一次建置要下載兩套 Chromium，約 10～20 分鐘。所有 base image（`python:3.13-slim-bookworm`、`node:22-bookworm-slim`、`nginx:1.27-alpine`）與 Playwright 的 Chromium 都有 arm64 版本，不需要修改 Dockerfile。

## 6. 設定網域與 HTTPS

### 6-1. 取得網域

- 已經有網域：新增一筆 `A` 記錄指向 VM 公開 IP。
- 沒有網域：到 [DuckDNS](https://www.duckdns.org/) 免費申請一個子網域（例如 `autotest-xxx.duckdns.org`），填入 VM 公開 IP。

### 6-2. 安裝 Caddy

Caddy 會自動申請並更新 Let's Encrypt 憑證。

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`（把網域換成自己的）：

```
autotest-xxx.duckdns.org {
    reverse_proxy 127.0.0.1:8080
}
```

```bash
sudo systemctl reload caddy
```

打開 `https://autotest-xxx.duckdns.org`，以 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 登入。

Caddy 會自動即時轉送 SSE（`text/event-stream`），也不限制上傳大小，不需要額外設定。它只信任自己看到的連線來源 IP，使用者偽造的 `X-Forwarded-For` 不會傳到後端，登入限流仍依真實 IP 計算。

## 7. 備份

資料都在 Docker volume `autotest_backend-data`（資料庫、附件、執行報告）與 `autotest_robot-scripts`。以下腳本用 SQLite 的 backup API 取得一致的資料庫快照，再把整個 volume 打包。

`~/backup.sh`：

```bash
#!/bin/sh
set -e
cd ~/AI_tset_platfrom
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p ~/backups
docker compose exec -T backend python -c "import sqlite3; s=sqlite3.connect('data/autotest.db'); d=sqlite3.connect('data/backup.db'); s.backup(d); d.close()"
docker run --rm -v autotest_backend-data:/data -v autotest_robot-scripts:/scripts -v ~/backups:/out alpine \
  tar czf /out/autotest-$STAMP.tar.gz --exclude=autotest.db --exclude=autotest.db-wal --exclude=autotest.db-shm /data /scripts
docker compose exec -T backend rm -f data/backup.db
find ~/backups -name 'autotest-*.tar.gz' -mtime +14 -delete
```

```bash
chmod +x ~/backup.sh
crontab -e   # 加入：0 3 * * * /home/ubuntu/backup.sh
```

壓縮檔裡的 `data/backup.db` 就是資料庫，還原時改名為 `autotest.db` 放回 volume。備份檔最好再複製到 VM 以外的地方（例如 Oracle Object Storage，Always Free 有 20 GB）。

## 8. 更新版本

```bash
cd ~/AI_tset_platfrom
git pull
docker compose up -d --build
```

每次啟動會自動套用資料庫 migration。

## 常見問題

**Q: 瀏覽器連不到網站**
依序檢查：Security List 有沒有開 80/443、VM 內 iptables 有沒有放行、`sudo systemctl status caddy`、`docker compose ps`。

**Q: Caddy 申請憑證失敗**
確認網域已指向 VM 公開 IP（`dig +short <網域>`），而且 80 port 從外部連得到。Let's Encrypt 要透過 80 port 驗證。

**Q: 登入後執行測試看不到即時進度**
確認是用 `https://` 連線。`APP_ENV=prod` 的 cookie 帶 `Secure`，用 `http://` 時瀏覽器不會送出。

**Q: 平行執行時記憶體不足**
每個 Chromium 約佔 300～500 MB。用 `docker stats` 觀察，必要時調低 `backend/.env` 的 `PARALLEL_MAX_WORKERS`，再執行 `docker compose up -d`。
