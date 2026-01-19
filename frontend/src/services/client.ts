import type { APIResponse } from '@/types'

// 获取环境变量 - 兼容 Vite (import.meta.env) 和 Jest (process.env)
function getEnv(key: string, defaultValue: string): string {
  // Node.js / Jest 环境
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key] || defaultValue
  }
  return defaultValue
}

const API_BASE = getEnv('VITE_API_BASE_URL', 'http://localhost:8000')
const IS_DEBUG = getEnv('VITE_ENABLE_DEBUG', 'false') === 'true'

/**
 * HTTP客户端基础 - 通用请求处理函数
 */
export async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<APIResponse<T>> {
  const startTime = Date.now()
  console.log(`[API Client] 开始请求: ${options?.method || 'GET'} ${API_BASE}${endpoint}`)

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    const responseTime = Date.now()
    const duration = responseTime - startTime
    console.log(`[API Client] 收到响应: ${response.status} ${response.statusText}, 耗时: ${duration}ms`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: '请求失败' }))
      console.error(`[API Client] 请求失败:`, error)
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    const data = await response.json()
    console.log(`[API Client] 响应数据:`, data)
    return { success: true, data }
  } catch (error) {
    const endTime = Date.now()
    const duration = endTime - startTime
    console.error(`[API Client] 请求异常, 总耗时: ${duration}ms, 错误:`, error)
    if (IS_DEBUG) console.error('API Error:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : '未知错误',
    }
  }
}
