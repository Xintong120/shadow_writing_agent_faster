// SSE服务 - 替换WebSocket，实现实时进度推送
// 功能：
//   - SSE连接管理
//   - 连接数监控
//   - 消息缓存和断点续传
//   - 自动重连

import type { BatchProgressMessage } from '@/types'

export interface SSECallbacks {
  onConnected?: (data: any) => void
  onProgress?: (data: BatchProgressMessage) => void
  onStep?: (data: BatchProgressMessage) => void
  onUrlCompleted?: (data: BatchProgressMessage) => void
  onCompleted?: (data: BatchProgressMessage) => void
  onError?: (error: string) => void
  onClose?: (code: number, reason: string) => void

  // 新增语义块级别进度回调
  onChunkingStarted?: (data: BatchProgressMessage) => void
  onChunkingCompleted?: (data: BatchProgressMessage) => void
  onChunksProcessingStarted?: (data: BatchProgressMessage) => void
  onChunkProgress?: (data: BatchProgressMessage) => void
  onChunksProcessingCompleted?: (data: BatchProgressMessage) => void
}

// SSE连接监控类
class SSEMonitor {
  static activeConnections = new Set<string>()

  static addConnection(url: string, eventSource: EventSource) {
    this.activeConnections.add(url)
    console.log(`[SSE Monitor] 连接数: ${this.activeConnections.size}/6`, {
      当前连接: Array.from(this.activeConnections),
      新增连接: url
    })

    // 超过5个时警告（留1个buffer）
    if (this.activeConnections.size >= 5) {
      console.warn('[SSE Monitor] SSE连接数接近上限！', this.activeConnections.size)
    }

    // 监听断开
    eventSource.addEventListener('error', () => {
      this.removeConnection(url)
    })

    eventSource.addEventListener('close', () => {
      this.removeConnection(url)
    })
  }

  static removeConnection(url: string) {
    this.activeConnections.delete(url)
    console.log(`[SSE Monitor] 连接断开: ${this.activeConnections.size}/6`, {
      剩余连接: Array.from(this.activeConnections),
      断开连接: url
    })
  }
}

// 消息去重类
class MessageDeduplicator {
  static processedIds = new Set<string>()

  static shouldProcess(message: BatchProgressMessage): boolean {
    const messageId = message.id || `${message.type}_${Date.now()}`

    if (this.processedIds.has(messageId)) {
      console.log('[SSE Deduplicator] 跳过重复消息:', messageId)
      return false
    }

    // 只保留最近100个消息ID
    if (this.processedIds.size > 100) {
      const firstId = this.processedIds.values().next().value
      this.processedIds.delete(firstId)
    }

    this.processedIds.add(messageId)
    return true
  }
}

export class SSEService {
  private eventSource: EventSource | null = null
  private taskId: string | null = null
  private callbacks: SSECallbacks = {}
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isManualClose = false
  private lastEventId: string | null = null

  /**
   * 连接到SSE端点
   * @param taskId 任务ID
   * @param callbacks 回调函数集合
   * @param lastEventId 最后收到的事件ID，用于断点续传
   */
  connect(taskId: string, callbacks: SSECallbacks, lastEventId?: string | null) {
    const connectStartTime = Date.now()
    console.log(`[SSE] connect()开始执行 - 时间: ${new Date(connectStartTime).toLocaleTimeString()}, taskId:`, taskId)

    if (this.eventSource?.readyState === EventSource.OPEN) {
      console.log('[SSE] 检测到已存在的OPEN连接，更新回调')
      this.updateCallbacks(callbacks)
      return
    }

    this.taskId = taskId
    this.callbacks = callbacks
    this.isManualClose = false
    this.lastEventId = lastEventId || null

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const url = `${baseUrl}/api/v1/progress/${taskId}`

    console.log('[SSE] 构建SSE URL:', url)
    console.log('[SSE] API_BASE_URL:', baseUrl)
    console.log('[SSE] taskId:', taskId)

    try {
      console.log('[SSE] 创建EventSource连接...')
      const eventSourceInit: EventSourceInit = {}

      // 添加Last-Event-ID头部用于断点续传
      if (this.lastEventId) {
        console.log('[SSE] 使用断点续传, Last-Event-ID:', this.lastEventId)
        // 注意：EventSource不支持自定义头部，这里通过URL参数传递
        const separator = url.includes('?') ? '&' : '?'
        const resumableUrl = `${url}${separator}last_event_id=${encodeURIComponent(this.lastEventId)}`
        this.eventSource = new EventSource(resumableUrl, eventSourceInit)
      } else {
        this.eventSource = new EventSource(url, eventSourceInit)
      }

      const eventSourceCreatedTime = Date.now()
      console.log(`[SSE] EventSource对象创建完成 - 耗时: ${eventSourceCreatedTime - connectStartTime}ms`)

      // 监听连接打开
      this.eventSource.onopen = () => {
        const openTime = Date.now()
        console.log(`[SSE] SSE连接成功建立 - 时间: ${new Date(openTime).toLocaleTimeString()}, taskId: ${taskId}`)
        console.log(`[SSE] 连接建立耗时: ${openTime - connectStartTime}ms`)

        // 添加到连接监控
        SSEMonitor.addConnection(url, this.eventSource!)

        this.reconnectAttempts = 0
        this.callbacks.onConnected?.({ taskId, timestamp: openTime })
      }

      // 监听消息
      this.eventSource.onmessage = (event) => {
        const msgTime = Date.now()
        console.log(`[SSE] 收到原始消息 - 时间: ${new Date(msgTime).toLocaleTimeString()}:`, event.data)

        try {
          const message: BatchProgressMessage = JSON.parse(event.data)
          console.log(`[SSE] 解析消息类型: ${message.type}`)

          // 更新lastEventId用于断点续传
          if (event.lastEventId) {
            this.lastEventId = event.lastEventId
          }

          // 去重检查
          if (!MessageDeduplicator.shouldProcess(message)) {
            return
          }

          this.handleMessage(message)
        } catch (error) {
          console.error('[SSE] 消息解析失败:', error)
          this.callbacks.onError?.('消息解析失败')
        }
      }

      // 监听错误
      this.eventSource.onerror = (event) => {
        console.error('[SSE] SSE连接错误:', event)

        // 检查连接状态
        if (this.eventSource) {
          console.log('[SSE] 当前连接状态:', this.eventSource.readyState)
        }

        this.callbacks.onError?.('SSE连接错误')

        // 非手动关闭时尝试重连
        if (!this.isManualClose && this.eventSource?.readyState === EventSource.CLOSED) {
          this.attemptReconnect()
        }
      }

    } catch (error) {
      console.error('[SSE] 创建EventSource失败:', error)
      this.callbacks.onError?.('无法建立SSE连接')
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: BatchProgressMessage): void {
    if (import.meta.env.VITE_ENABLE_DEBUG === 'true') {
      console.log('[SSE] 处理消息:', message)
    }

    switch (message.type) {
      case 'connected':
        // 连接确认消息，不需要特殊处理
        break

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

      // 新增语义块级别消息处理
      case 'chunking_started':
        if (this.callbacks.onChunkingStarted) {
          this.callbacks.onChunkingStarted(message)
        } else {
          console.log('[SSE] chunking_started消息未处理，缺少回调函数')
        }
        break

      case 'chunking_completed':
        if (this.callbacks.onChunkingCompleted) {
          this.callbacks.onChunkingCompleted(message)
        } else {
          console.log('[SSE] chunking_completed消息未处理，缺少回调函数')
        }
        break

      case 'chunks_processing_started':
        if (this.callbacks.onChunksProcessingStarted) {
          this.callbacks.onChunksProcessingStarted(message)
        } else {
          console.log('[SSE] chunks_processing_started消息未处理，缺少回调函数')
        }
        break

      case 'chunk_progress':
        if (this.callbacks.onChunkProgress) {
          this.callbacks.onChunkProgress(message)
        } else {
          console.log('[SSE] chunk_progress消息未处理，缺少回调函数')
        }
        break

      case 'chunks_processing_completed':
        if (this.callbacks.onChunksProcessingCompleted) {
          this.callbacks.onChunksProcessingCompleted(message)
        } else {
          console.log('[SSE] chunks_processing_completed消息未处理，缺少回调函数')
        }
        break

      default:
        if (import.meta.env.VITE_ENABLE_DEBUG === 'true') {
          console.warn('[SSE] 未知消息类型:', message.type)
        }
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SSE] 重连失败: 达到最大重试次数')
      this.callbacks.onError?.('无法重新连接到服务器')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * this.reconnectAttempts

    if (import.meta.env.VITE_ENABLE_DEBUG === 'true') {
      console.log(`[SSE] 尝试重连 ${this.reconnectAttempts}/${this.maxReconnectAttempts} 在 ${delay}ms 后`)
    }

    setTimeout(() => {
      if (this.taskId) {
        this.connect(this.taskId, this.callbacks, this.lastEventId)
      }
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true

    if (this.eventSource) {
      try {
        this.eventSource.close()
        console.log('[SSE] SSE连接已手动关闭')
      } catch (error) {
        console.error('[SSE] 关闭SSE连接失败:', error)
      }
      this.eventSource = null
    }

    this.taskId = null
    this.callbacks = {}
    this.reconnectAttempts = 0
    this.lastEventId = null
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    const connected = this.eventSource?.readyState === EventSource.OPEN
    console.log(`[SSE] isConnected() 检查结果: ${connected}, readyState: ${this.eventSource?.readyState}`)
    return connected
  }

  /**
   * 更新回调函数
   */
  updateCallbacks(callbacks: SSECallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks }
  }

  /**
   * 获取当前任务ID
   */
  getCurrentTaskId(): string | null {
    return this.taskId
  }

  /**
   * 获取最后事件ID（用于断点续传）
   */
  getLastEventId(): string | null {
    return this.lastEventId
  }

  /**
   * 获取活跃连接数
   */
  static getActiveConnectionCount(): number {
    return SSEMonitor.activeConnections.size
  }
}

// 创建单例实例
export const sseService = new SSEService()

export default sseService
