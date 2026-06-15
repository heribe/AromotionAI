# AromotionAI 部署指南

单机部署：Linux VPS + Docker Compose。两个容器（前端 nginx + 后端 FastAPI），SQLite 持久化到宿主机卷。

```
浏览器 → :80 nginx ─┬─ 前端静态文件
                    └─ /api/v1 反代 → backend:8000 (FastAPI + Playwright + ffmpeg)
                                          └─ SQLite / media / cookies (宿主机卷)
```

## 一、前置准备

### 1. 服务器要求
- Linux（推荐 Ubuntu 22.04+）
- 已安装 **Docker** 和 **Docker Compose**（v2+，`docker compose` 命令）
- 内存 ≥ 2GB（Playwright chromium 较吃内存）
- 能访问外网（调抖音 API + 智谱 GLM API）

安装 Docker（Ubuntu 示例）：
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 重新登录生效
docker --version && docker compose version   # 验证
```

### 2. 物料准备
- **智谱 GLM API Key**：https://open.bigmodel.cn/ 获取
- **抖音 Cookie**：浏览器登录抖音后用 EditThisCookie 等插件导出 JSON 数组格式，保存为 `douyin.json`

## 二、部署步骤

### 1. 上传代码到服务器
```bash
# 方式一：git clone（推荐）
git clone <repo-url> aromotion
cd aromotion

# 方式二：本地打包上传
# 本地：tar czf aromotion.tar.gz --exclude=node_modules --exclude=.venv --exclude=backend/data .
# scp aromotion.tar.gz user@server:~/
# 服务器：tar xzf aromotion.tar.gz -C aromotion && cd aromotion
```

### 2. 配置环境变量
```bash
cp backend/.env.example backend/.env
nano backend/.env
# 填入 GLM_API_KEY=（必填）
# ZHIPUAI_BASE_URL 按你的套餐：Coding Plan 用默认值，标准套餐留空
```

> docker compose 直接读取 `backend/.env`（见 `docker-compose.yml` 的 `env_file`），
> 与本地开发共用同一份配置，无需在根目录另建 `.env`。

### 3. 放置抖音 Cookie
```bash
mkdir -p backend/data/cookies
# 把本地导出的 douyin.json 上传到这里
# 方式一：scp
#   scp douyin.json user@server:~/aromotion/backend/data/cookies/
# 方式二：nano 粘贴内容
nano backend/data/cookies/douyin.json
```

> Cookie 是 JSON 数组格式，形如 `[{"name":"...","value":"...","domain":"..."}, ...]`。

### 4. 构建并启动
```bash
docker compose up -d --build
```
- 首次构建较慢（拉 Playwright 镜像 ~1.5GB + 装 chromium 依赖 + 前端 npm build），约 5-15 分钟。
- 后续启动秒级（镜像已缓存）。

### 5. 验证
```bash
# 容器状态
docker compose ps

# 后端健康检查
curl http://localhost/health        # 经 nginx
curl http://localhost/api/v1/cookies/status   # 应返回 douyin is_valid:true

# 查看日志（有问题先看这里）
docker compose logs -f backend
docker compose logs -f frontend
```

浏览器访问 `http://<服务器IP>`，应看到工作台页面。

## 三、日常运维

### 查看日志
```bash
docker compose logs -f backend     # 后端实时日志
docker compose logs -f frontend    # nginx 日志
docker compose logs --tail 100 backend   # 最近 100 行
```

### 重启服务
```bash
docker compose restart backend     # 只重启后端（改了 .env 后）
docker compose restart             # 重启全部
```

### 更新代码
```bash
git pull
docker compose up -d --build       # 重新构建改动的镜像
```

### Cookie 失效后
抖音 Cookie 会过期（表现为采集失败、报权限错误）。更新：
```bash
# 本地重新导出 douyin.json，上传覆盖
scp douyin.json user@server:~/aromotion/backend/data/cookies/
docker compose restart backend     # 重启让采集器重新读取
```

### 备份数据
```bash
# 备份 SQLite + 媒体 + cookie（backend/data 目录）
tar czf aromotion-backup-$(date +%Y%m%d).tar.gz backend/data/
# 下载到本地
scp user@server:~/aromotion/aromotion-backup-*.tar.gz ./
```

## 四、架构说明

### 文件清单
| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 编排两个服务（backend + frontend）|
| `backend/Dockerfile` | 后端镜像：Playwright 官方镜像 + ffmpeg + uv |
| `frontend/Dockerfile` | 前端镜像：node 构建 → nginx 托管 |
| `frontend/nginx.conf` | 静态托管 + SPA fallback + 反代后端（含 SSE 配置）|
| `backend/.env` | 环境变量（GLM_API_KEY 等，不入库，本地开发与部署共用）|
| `backend/data/` | 持久化数据（db / media / cookies）|

### 数据卷
挂载到宿主机 `./backend/data/`，容器重建不丢：
```
./backend/data/db/        # SQLite 数据库（aromotion.db）
./backend/data/media/     # 下载的封面图、视频帧、头像
./backend/data/cookies/   # 抖音 cookie（douyin.json）
```

### SSE 注意事项
任务进度推送走 SSE（`/api/v1/analysis/{id}/progress`）。nginx 已单独配置：
- `proxy_buffering off`（关闭缓冲，否则事件不实时推送）
- `proxy_read_timeout 600s`（长任务 10 分钟超时）

## 五、常见问题

### Q: 首次 `docker compose up --build` 很慢？
正常。Playwright 镜像 ~1.5GB，chromium 依赖多。后续构建走缓存会快很多。

### Q: 后端容器启动后立即退出？
```bash
docker compose logs backend
```
常见原因：
- `backend/.env` 没填 `GLM_API_KEY`（必填）
- Playwright 在容器内权限问题（已用官方镜像规避）

### Q: 采集抖音报错 / cookie 失效？
看 `docker compose logs backend` 找报错。多半是 cookie 过期，按上面「Cookie 失效后」更新。

### Q: 任务进度页卡住不动？
检查 SSE 是否被缓冲：
```bash
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
# 确认 progress location 块有 proxy_buffering off
```

### Q: 想换端口（80 被占用）？
改 `docker-compose.yml` 里 `ports: - "80:80"` 为 `"8080:80"`，访问 `http://<IP>:8080`。

### Q: 想要 HTTPS / 域名？
当前是 HTTP + IP。要 HTTPS 时，在 `frontend/nginx.conf` 加 443 监听 + 证书，或在前置一层 Caddy/Traefik 自动 HTTPS。后续可补。

## 六、本地开发（非容器）
前后端本地开发方式见根目录 [README.md](README.md) 的「快速开始」。容器部署与本地开发互不影响。
