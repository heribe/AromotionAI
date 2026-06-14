# AromotionAI 前端镜像（多阶段构建）
# Stage 1: node 构建 Vite 产物
# Stage 2: nginx 托管静态文件

# ---------- Stage 1: 构建 ----------
FROM node:20-slim AS builder

WORKDIR /build

# 先拷依赖描述，利用层缓存
COPY package.json package-lock.json ./

# 装全部依赖（含 devDependencies：构建需要 typescript / vite）
RUN npm ci

# 拷源码 + 环境配置
COPY . .

# 生产构建（读取 .env.production）
RUN npm run build

# ---------- Stage 2: 运行 ----------
FROM nginx:alpine

# 拷贝自定义 nginx 配置（静态托管 + SPA fallback + 反代后端）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
