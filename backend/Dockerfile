# AromotionAI 后端镜像
# 基于 Playwright 官方 Python 镜像（自带 chromium + 系统依赖，省去手动安装的坑）
# 镜像较大（~1.5GB），但自用场景稳定优先。
#
# 注意：tag 的 playwright 版本需与 pyproject.toml 装出来的版本一致（当前 1.60.0）。
# 升级 playwright 时同步改这里。

FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

# 系统依赖：ffmpeg（视频抽帧）。chromium 及其系统库已由基础镜像提供。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（与本地一致的包管理器，构建快）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先拷依赖描述，利用 Docker 层缓存（依赖变动少时跳过重装）
COPY pyproject.toml uv.lock ./

# 同步生产依赖（不含 dev 组）。
# 注：uv.lock 若含平台特定条目，uv 会按当前 Linux 平台选择兼容版本。
RUN uv sync --no-dev

# 拷贝应用代码
COPY app/ ./app/
COPY README.md ./

# 数据目录（运行时由 compose 挂载卷覆盖，这里只保证默认路径存在）
RUN mkdir -p /app/data/db /app/data/media /app/data/cookies

# 暴露 FastAPI 端口
EXPOSE 8000

# 容器内通过 uv 运行 uvicorn
# --host 0.0.0.0 必须加上，否则只监听 127.0.0.1，容器外访问不到
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
