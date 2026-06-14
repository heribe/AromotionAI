/**
 * HTTP 客户端 — 与后端 /api/v1 通信的底座
 *
 * 设计要点：
 * 1. baseURL 用相对路径 `/api/v1`，配合 vite.config.ts 的 server.proxy 转发到后端
 *    （开发环境，同源避免 CORS；生产环境由网关/反向代理处理）。
 * 2. 响应拦截器统一解包后端的 BaseResponse 信封 {code, message, data}：
 *    - code === 0：把 response.data 替换为 envelope.data（业务层只关心业务数据）
 *    - code !== 0：抛 ApiError，message 来自后端
 * 3. HTTP 层错误（非 2xx，FastAPI 抛 HTTPException）由 axios 走 error 分支，
 *    FastAPI 的 detail 字段放在 error.response.data.detail，统一规整到 ApiError.message。
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

/** 后端统一响应信封 */
export interface BaseResponse<T = unknown> {
  code: number;
  message: string;
  data: T | null;
}

/** 业务/HTTP 错误统一形态 */
export class ApiError extends Error {
  /** HTTP 状态码（业务错误时为 200，靠 code 区分） */
  status: number;
  /** 后端 BaseResponse.code（HTTP 错误时为 -1） */
  code: number;
  /** 原始数据（调试用） */
  raw?: unknown;

  constructor(message: string, status: number, code: number, raw?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.raw = raw;
  }
}

/** 是否为后端信封结构 */
function isBaseResponse(obj: unknown): obj is BaseResponse {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'code' in obj &&
    'message' in obj &&
    'data' in obj
  );
}

const rawInstance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api/v1',
  timeout: 120000, // 分析/香调生成可能较慢，给 2 分钟
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器：预留 token 注入点（当前后端无鉴权）
rawInstance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // const token = localStorage.getItem('token');
  // if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截器：解包信封
// 把 response.data（即 BaseResponse 信封）替换为 envelope.data，
// 这样调用方拿到的 response.data 就是纯业务数据。
rawInstance.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (isBaseResponse(body)) {
      if (body.code === 0) {
        response.data = body.data;
        return response;
      }
      // 业务错误：code !== 0
      throw new ApiError(body.message || '业务错误', response.status, body.code, body);
    }
    // 非信封结构（如 SSE/文件流/健康检查）：原样返回
    return response;
  },
  (error) => {
    if (error.response) {
      // FastAPI HTTPException：detail 在 response.data.detail
      const detail =
        (error.response.data && (error.response.data.detail || error.response.data.message)) ||
        error.message;
      throw new ApiError(
        typeof detail === 'string' ? detail : JSON.stringify(detail),
        error.response.status,
        -1,
        error.response.data,
      );
    }
    // 网络错误 / 超时
    throw new ApiError(error.message || '网络错误', 0, -1);
  },
);

/**
 * 类型化的 HTTP 客户端。
 *
 * 响应拦截器已解包 BaseResponse 信封，response.data 即业务数据。
 * 业务层调用形如 `http.get<AnalysisListData>('/analysis/list')`。
 */
export const http = {
  get: <T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> =>
    rawInstance.get(url, { params }).then((r) => r.data as T),
  post: <T = unknown>(url: string, body?: unknown): Promise<T> =>
    rawInstance.post(url, body).then((r) => r.data as T),
  put: <T = unknown>(url: string, body?: unknown): Promise<T> =>
    rawInstance.put(url, body).then((r) => r.data as T),
  delete: <T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> =>
    rawInstance.delete(url, { params }).then((r) => r.data as T),
};

export default http;
