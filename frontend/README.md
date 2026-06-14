# AromotionAI Frontend

AromotionAI 前端项目，基于 **React 19 + Vite 8 + TypeScript + Ant Design 6**。

> 项目总体介绍、架构与产品流程见[根目录 README](../README.md)。

---

## 一、环境要求

| 工具 | 最低版本 |
|---|---|
| Node.js | 18+ |
| npm | 9+ |

---

## 二、快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev          # → http://localhost:5173
```

### 脚本说明

| 命令 | 作用 |
|---|---|
| `npm run dev` | 启动 Vite 开发服务器（HMR） |
| `npm run build` | `tsc -b` 类型检查 + Vite 生产构建 |
| `npm run preview` | 本地预览生产构建产物 |
| `npm run lint` | ESLint 代码检查 |

---

## 三、目录结构

```
frontend/
├── public/                     # 静态资源
├── src/
│   ├── main.tsx                # 应用入口
│   ├── App.tsx                 # 根组件
│   ├── index.css               # 全局样式
│   ├── router/                 # 路由配置（懒加载分包）
│   ├── pages/                  # 页面
│   │   ├── Dashboard/          # 首页 / 任务工作台
│   │   ├── ProfileReport/      # 画像报告（四维度 + 图表）
│   │   ├── TagSelection/       # 标签筛选
│   │   └── FragranceRecommend/ # 调配室（三栏工作台）
│   ├── components/             # 公共与布局组件
│   │   └── layout/             # 全局布局
│   ├── services/               # API 调用封装 + Mock 数据
│   ├── stores/                 # Zustand 状态管理
│   ├── types/                  # TypeScript 类型定义
│   └── utils/                  # 工具函数
├── vite.config.ts
├── tsconfig.json
└── eslint.config.js
```

---

## 四、路由

| 路径 | 页面 | 说明 |
|---|---|---|
| `/dashboard` | Dashboard | 首页，默认入口（`/` 重定向到此） |
| `/report/:taskId` | ProfileReport | 画像报告 |
| `/tags/:taskId` | TagSelection | 标签筛选 |
| `/recommend` | FragranceRecommend | 香调调配室 |

所有页面均通过 `React.lazy` 懒加载，首屏只加载当前路由代码。

---

## 五、路径别名

`@` 指向 `src/`，配置见 `vite.config.ts`。

```ts
// 推荐
import { useAnalysisStore } from '@/stores/useAnalysisStore';
```

---

## 六、与后端联调

### 当前状态

前端目前**未接入真实 API**，所有数据来自 Mock：

| 文件 | 用途 |
|---|---|
| `src/services/mockData.ts` | Part1 画像分析 Mock 数据 |
| `src/services/mockFragranceData.ts` | Part2 香调推荐 Mock 数据 |

**无需后端即可完整预览全部页面**。

### 后端接入计划

后端（FastAPI）开发完成后：

1. 在 `src/services/` 下新增 Axios 实例与各业务 API 封装（`analysisService.ts` / `fragranceService.ts` 等）
2. 通过环境变量配置 API 基础地址：

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
```

3. 将 Mock 数据调用替换为真实 API，SSE 进度接入 `EventSource`

后端 API 契约详见 [`docs/00-global-dev-guide.md`](../docs/00-global-dev-guide.md) 第四章。

---

## 七、开发约定

- 组件使用函数式组件 + Hooks
- 组件文件名使用 `PascalCase`，工具函数使用 `camelCase`
- 类型定义优先使用 `interface`
- 页面目录可包含 `index.tsx` + `components/` 子目录
- UI 设计语言遵循「Natural Artisan Ledger」：浅冷陶瓷背景 + 深苔藓绿文字 + 琥珀点缀，1px 实线边框，**严禁使用系统 Emoji**，图标统一使用 `lucide-react`

完整设计与开发规范见 [`docs/`](../docs/) 与 [`GEMINI.md`](../GEMINI.md)。
