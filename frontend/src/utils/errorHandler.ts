import { toast } from 'sonner'
import {
  AppError,
  APIError,
  NetworkError,
  ValidationError,
  WebSocketError,
  TimeoutError,
} from './errors'

const IS_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true'

/**
 * 错误消息映射
 */
const ERROR_MESSAGES: Record<string, string> = {
  API_ERROR: 'API 请求失败',
  NETWORK_ERROR: '网络连接失败',
  VALIDATION_ERROR: '输入验证失败',
  WEBSOCKET_ERROR: 'WebSocket 连接错误',
  TIMEOUT_ERROR: '请求超时',
  UNKNOWN_ERROR: '发生未知错误',
}

/**
 * 统一错误处理函数
 */
export function handleError(error: unknown, context?: string): void {
  // 开发模式下打印详细错误
  if (IS_DEBUG) {
    console.error(`[Error] ${context || 'Unknown'}:`, error)
  }

  // 根据错误类型显示不同提示
  if (error instanceof ValidationError) {
    toast.error(error.message, {
      description: error.details?.field
        ? `字段：${error.details.field}`
        : undefined,
    })
  } else if (error instanceof APIError) {
    const message =
      error.statusCode === 404
        ? '请求的资源不存在'
        : error.statusCode === 500
        ? '服务器内部错误'
        : error.message

    toast.error(message, {
      description: IS_DEBUG ? `状态码：${error.statusCode}` : undefined,
      action: error.statusCode === 500
        ? {
            label: '重试',
            onClick: () => window.location.reload(),
          }
        : undefined,
    })
  } else if (error instanceof NetworkError) {
    toast.error(error.message, {
      description: '请检查网络连接',
      action: {
        label: '重试',
        onClick: () => window.location.reload(),
      },
    })
  } else if (error instanceof TimeoutError) {
    toast.error(error.message, {
      description: '请稍后重试',
    })
  } else if (error instanceof WebSocketError) {
    toast.error(error.message, {
      description: 'WebSocket 连接异常',
    })
  } else if (error instanceof AppError) {
    toast.error(error.message)
  } else if (error instanceof Error) {
    toast.error(error.message || ERROR_MESSAGES.UNKNOWN_ERROR)
  } else {
    toast.error(ERROR_MESSAGES.UNKNOWN_ERROR)
  }
}

/**
 * 异步错误包装器
 */
export function withErrorHandler<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  context?: string
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args)
    } catch (error) {
      handleError(error, context)
      throw error
    }
  }) as T
}

/**
 * React 组件错误处理 Hook
 */
export function useErrorHandler() {
  return (error: unknown, context?: string) => {
    handleError(error, context)
  }
}