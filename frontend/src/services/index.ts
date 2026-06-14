/**
 * 数据源门面 — 根据 VITE_USE_MOCK 切换真实后端 / Mock
 *
 * 使用方式：
 *   import { analysisApi } from '@/services';
 *   const list = await analysisApi.getTaskList();
 *
 * 环境变量：
 *   VITE_USE_MOCK=true  → 走 mockData（无需后端即可预览，默认开发体验）
 *   VITE_USE_MOCK=false（或未设）→ 走真实 /api/v1
 *
 * 各阶段逐步补全真实 api 方法；未补全的方法会抛错提示。
 */
import { mockApi } from './mockData';
import * as realApi from './api';

export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK ?? 'false') === 'true';

/**
 * Part 1 分析数据源。
 *
 * 签名对齐 mockApi：getTaskList / getReport / getTags / createTask。
 * 真实实现按阶段补全，未实现的方法抛错。
 */
export const analysisApi = USE_MOCK
  ? mockApi
  : {
      getTaskList: realApi.getTaskList,
      createTask: realApi.createTask,
      getReport: realApi.getReport,
      getTags: realApi.getTags,
    };

// Part 2 香调数据源（阶段 5 补全）
export { };
