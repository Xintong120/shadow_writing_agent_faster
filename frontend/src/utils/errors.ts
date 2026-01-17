/**
 * 基础错误类
 */
export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message)
    this.name = 'AppError'
  }
}

/**
 * API 错误
 */
export class APIError extends AppError {
  constructor(message: string, statusCode: number, details?: any) {
    super(message, 'API_ERROR', statusCode, details)
    this.name = 'APIError'
  }
}

/**
 * 网络错误
 */
export class NetworkError extends AppError {
  constructor(message: string = '网络连接失败，请检查网络') {
    super(message, 'NETWORK_ERROR')
    this.name = 'NetworkError'
  }
}

/**
 * 验证错误
 */
export class ValidationError extends AppError {
  constructor(message: string, field?: string) {
    super(message, 'VALIDATION_ERROR', 400, { field })
    this.name = 'ValidationError'
  }
}

/**
 * WebSocket 错误
 */
export class WebSocketError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 'WEBSOCKET_ERROR', undefined, details)
    this.name = 'WebSocketError'
  }
}

/**
 * 超时错误
 */
export class TimeoutError extends AppError {
  constructor(message: string = '请求超时') {
    super(message, 'TIMEOUT_ERROR', 408)
    this.name = 'TimeoutError'
  }
}