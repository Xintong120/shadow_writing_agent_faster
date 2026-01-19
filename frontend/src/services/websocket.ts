import type { BatchProgressMessage } from '@/types'

// 绕过Vite代理，直接连接后端WebSocket
// 开发模式: 直接连接 ws://localhost:8000
// 生产模式: 使用环境变量配置的URL
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const IS_DEBUG = import.meta.env.VITE_ENABLE_DEBUG === 'true'

export interface WebSocketCallbacks {
  onConnected?: (data: any) => void
  onProgress?: (data: BatchProgressMessage) => void
  onStep?: (data: BatchProgressMessage) => void
  onUrlCompleted?: (data: BatchProgressMessage) => void
  onCompleted?: (data: BatchProgressMessage) => void
  onError?: (error: string) => void
  onClose?: (code: number, reason: string) => void
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private taskId: string | null = null
  private callbacks: WebSocketCallbacks = {}
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private heartbeatInterval: NodeJS.Timeout | null = null
  private isManualClose = false

  /**
   * 初始化WebSocket连接（应用启动时调用）
   * 仅用于测试连接，不处理业务消息
   */
  initialize(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      if (IS_DEBUG) console.log('WebSocket already connected')
      return
    }

    this.isManualClose = false

    // 使用一个测试taskId来验证连接
    const testTaskId = 'connection_test'
    const wsUrl = `${WS_BASE}/ws/progress/${testTaskId}`
    console.log('[WebSocket] 初始化WebSocket连接:', wsUrl)

    try {
      console.log('[WebSocket] 创建WebSocket连接...')
      this.ws = new WebSocket(wsUrl)
      console.log('[WebSocket] WebSocket对象创建成功，readyState:', this.ws.readyState)

      this.ws.onopen = () => {
        const openTime = Date.now()
        console.log(`[WebSocket] 应用启动WebSocket连接成功建立！时间: ${new Date(openTime).toLocaleTimeString()}`)
        console.log('[WebSocket] 连接URL:', wsUrl)
        console.log('[WebSocket] 连接状态:', this.ws.readyState)
        if (IS_DEBUG) console.log('WebSocket initialized and connected')
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.callbacks.onConnected?.({ taskId: null, timestamp: openTime })
        // 连接测试成功后立即关闭，不占用资源
        setTimeout(() => this.disconnect(), 1000)
      }

      this.ws.onmessage = (event) => {
        console.log('[WebSocket] 收到测试消息:', event.data)
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.callbacks.onError?.('WebSocket连接错误')
      }

      this.ws.onclose = (event) => {
        if (IS_DEBUG) console.log('WebSocket test connection closed:', event.code, event.reason)
        this.stopHeartbeat()
        this.callbacks.onClose?.(event.code, event.reason)
      }
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
      this.callbacks.onError?.('无法初始化WebSocket连接')
    }
  }

  /**
   * 订阅特定任务的消息
   * @param taskId 任务ID
   * @param callbacks 回调函数集合
   */
  subscribeTask(taskId: string, callbacks: WebSocketCallbacks): void {
    console.log('[WebSocket] 订阅任务消息:', taskId)
    this.taskId = taskId
    this.callbacks = callbacks

    // 如果WebSocket已连接，发送订阅消息
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({
          type: 'subscribe',
          taskId: taskId
        }))
        console.log('[WebSocket] 发送订阅消息:', taskId)
      } catch (error) {
        console.error('Failed to send subscribe message:', error)
      }
    }
  }

  /**
   * 连接到WebSocket服务器（兼容旧API）
   * @param taskId 任务ID
   * @param callbacks 回调函数集合
   */
  connect(taskId: string, callbacks: WebSocketCallbacks): void {
    const connectStartTime = Date.now()
    console.log(`[WebSocket] connect()方法开始执行 - 时间: ${new Date(connectStartTime).toLocaleTimeString()}, taskId:`, taskId)

    if (this.ws?.readyState === WebSocket.OPEN) {
      // 如果已经连接，直接订阅任务
      console.log('[WebSocket] 检测到已存在的OPEN连接，调用subscribeTask')
      this.subscribeTask(taskId, callbacks)
      return
    }

    // 如果没有连接，先初始化连接
    console.log('[WebSocket] 开始初始化新连接')
    this.taskId = taskId
    this.callbacks = callbacks
    this.isManualClose = false

    const wsUrl = `${WS_BASE}/ws/progress/${taskId}`
    console.log('[WebSocket] 构建WebSocket URL:', wsUrl)
    console.log('[WebSocket] WS_BASE:', WS_BASE)
    console.log('[WebSocket] taskId:', taskId)

    try {
      console.log('[WebSocket] 创建WebSocket连接对象...')
      const wsCreateTime = Date.now()
      this.ws = new WebSocket(wsUrl)
      const wsCreatedTime = Date.now()
      console.log(`[WebSocket] WebSocket对象创建完成 - 耗时: ${wsCreatedTime - wsCreateTime}ms, readyState:`, this.ws.readyState)

      // 监听连接事件
      console.log('[WebSocket] 设置事件监听器')

      this.ws.onopen = () => {
        const openTime = Date.now()
        console.log(`[WebSocket] WebSocket连接成功建立 - 时间: ${new Date(openTime).toLocaleTimeString()}, taskId: ${taskId}`)
        console.log(`[WebSocket] 连接建立耗时: ${openTime - connectStartTime}ms`)
        this.reconnectAttempts = 0
        this.startHeartbeat()
        console.log('[WebSocket] 启动心跳检测')
        this.callbacks.onConnected?.({ taskId, timestamp: openTime })
      }

      this.ws.onmessage = (event) => {
        const msgTime = Date.now()
        console.log(`[WebSocket] 收到原始消息 - 时间: ${new Date(msgTime).toLocaleTimeString()}:`, event.data)
        try {
          const message: BatchProgressMessage = JSON.parse(event.data)
          console.log(`[WebSocket] 解析消息类型: ${message.type}`)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.callbacks.onError?.('WebSocket连接错误')
      }

      this.ws.onclose = (event) => {
        if (IS_DEBUG) console.log('WebSocket closed:', event.code, event.reason)
        this.stopHeartbeat()

        this.callbacks.onClose?.(event.code, event.reason)

        // 非正常关闭且非手动关闭时尝试重连
        if (!this.isManualClose && event.code !== 1000) {
          this.attemptReconnect()
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.callbacks.onError?.('无法建立WebSocket连接')
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: BatchProgressMessage): void {
    if (IS_DEBUG) console.log('WebSocket message:', message)

    switch (message.type) {
      case 'started':
        this.callbacks.onProgress?.(message)
        break

      case 'progress':
        this.callbacks.onProgress?.(message)
        break

      case 'step':
        this.callbacks.onStep?.(message)
        break

      case 'url_completed':
        this.callbacks.onUrlCompleted?.(message)
        break

      case 'completed':
        this.callbacks.onCompleted?.(message)
        this.disconnect() // 任务完成，主动断开连接
        break

      case 'error':
        this.callbacks.onError?.(message.error || '处理过程中发生错误')
        break

      default:
        if (IS_DEBUG) console.warn('Unknown message type:', message.type)
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket reconnection failed: max attempts reached')
      this.callbacks.onError?.('无法重新连接到服务器')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * this.reconnectAttempts

    if (IS_DEBUG) {
      console.log(`Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
    }

    setTimeout(() => {
      if (this.taskId) {
        this.connect(this.taskId, this.callbacks)
      }
    }, delay)
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping' }))
        } catch (error) {
          console.error('Failed to send heartbeat:', error)
        }
      }
    }, 30000) // 每30秒发送一次心跳
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.ws) {
      try {
        this.ws.close(1000, 'Client closed connection')
      } catch (error) {
        console.error('Failed to close WebSocket:', error)
      }
      this.ws = null
    }

    this.taskId = null
    this.callbacks = {}
    this.reconnectAttempts = 0
  }

  /**
   * 检查是否完全连接（OPEN状态）
   */
  isConnected(): boolean {
    const connected = this.ws?.readyState === WebSocket.OPEN
    console.log(`[WebSocket] isConnected() 检查结果: ${connected}, readyState: ${this.ws?.readyState}`)
    return connected
  }

  /**
   * 更新回调函数（用于重新设置消息处理器）
   */
  updateCallbacks(callbacks: WebSocketCallbacks): void {
    this.callbacks = callbacks
  }

  /**
   * 获取当前任务ID
   */
  getCurrentTaskId(): string | null {
    return this.taskId
  }
}

// 创建单例实例
export const websocketService = new WebSocketService()

export default websocketService
