// SSE服务 - 预连接机制 + 埋点监控
// 功能：
//   - SSE预连接机制，避免连接延迟
//   - 连接生命周期埋点监控
//   - 自动重连和健康检查
//   - 消息缓存和断点续传

import type { BatchProgressMessage } from "@/types";

export interface SSECallbacks {
  onConnected?: (data: any) => void;
  onProgress?: (data: BatchProgressMessage) => void;
  onStep?: (data: BatchProgressMessage) => void;
  onUrlCompleted?: (data: BatchProgressMessage) => void;
  onCompleted?: (data: BatchProgressMessage) => void;
  onError?: (error: string) => void;
  onClose?: (code: number, reason: string) => void;

  // 新增语义块级别进度回调
  onChunkingStarted?: (data: BatchProgressMessage) => void;
  onChunkingCompleted?: (data: BatchProgressMessage) => void;
  onChunksProcessingStarted?: (data: BatchProgressMessage) => void;
  onChunkProgress?: (data: BatchProgressMessage) => void;
  onChunksProcessingCompleted?: (data: BatchProgressMessage) => void;
  onChunkCompleted?: (data: BatchProgressMessage) => void;
}

// SSE连接监控类
class SSEMonitor {
  static activeConnections = new Set<string>();

  static addConnection(url: string, eventSource: EventSource) {
    this.activeConnections.add(url);
    console.log(`[SSE Monitor] 连接数: ${this.activeConnections.size}/6`, {
      当前连接: Array.from(this.activeConnections),
      新增连接: url,
    });

    // 超过5个时警告（留1个buffer）
    if (this.activeConnections.size >= 5) {
      console.warn(
        "[SSE Monitor] SSE连接数接近上限！",
        this.activeConnections.size,
      );
    }

    // 监听断开
    eventSource.addEventListener("error", () => {
      this.removeConnection(url);
    });

    eventSource.addEventListener("close", () => {
      this.removeConnection(url);
    });
  }

  static removeConnection(url: string) {
    this.activeConnections.delete(url);
    console.log(`[SSE Monitor] 连接断开: ${this.activeConnections.size}/6`, {
      剩余连接: Array.from(this.activeConnections),
      断开连接: url,
    });
  }
}

// 消息去重类
class MessageDeduplicator {
  static processedIds = new Set<string>();

  static shouldProcess(message: BatchProgressMessage): boolean {
    const messageId = message.id || `${message.type}_${Date.now()}`;

    if (this.processedIds.has(messageId)) {
      console.log("[SSE Deduplicator] 跳过重复消息:", messageId);
      return false;
    }

    // 只保留最近100个消息ID
    if (this.processedIds.size > 100) {
      const firstId = this.processedIds.values().next().value;
      this.processedIds.delete(firstId);
    }

    this.processedIds.add(messageId);
    return true;
  }
}

export class SSEService {
  private eventSource: EventSource | null = null;
  private taskId: string | null = null;
  private callbacks: SSECallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private isManualClose = false;
  private lastEventId: string | null = null;

  /**
   * 连接到SSE端点
   * @param taskId 任务ID
   * @param callbacks 回调函数集合
   * @param lastEventId 最后收到的事件ID，用于断点续传
   */
  connect(
    taskId: string,
    callbacks: SSECallbacks,
    lastEventId?: string | null,
  ) {
    const connectStartTime = Date.now();
    console.log(
      `[SSE诊断] connect()开始执行 - 时间: ${new Date(connectStartTime).toLocaleTimeString()}, taskId:`,
      taskId,
    );
    console.log(`[SSE诊断] 连接开始时间戳: ${connectStartTime}`);

    if (this.eventSource?.readyState === EventSource.OPEN) {
      console.log("[SSE诊断] 检测到已存在的OPEN连接，更新回调");
      this.updateCallbacks(callbacks);
      return;
    }

    // 记录连接前的状态
    console.log(`[SSE诊断] 连接前状态检查:`);
    console.log(`  - 当前eventSource存在: ${!!this.eventSource}`);
    console.log(`  - 当前readyState: ${this.eventSource?.readyState}`);
    console.log(`  - 当前taskId: ${this.taskId}`);
    console.log(`  - 手动关闭标志: ${this.isManualClose}`);

    this.taskId = taskId;
    this.callbacks = callbacks;
    this.isManualClose = false;
    this.lastEventId = lastEventId || null;

    const baseUrl =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const url = `${baseUrl}/api/v1/progress/${taskId}`;

    console.log(`[SSE诊断] 构建SSE URL: ${url}`);
    console.log(`[SSE诊断] API_BASE_URL: ${baseUrl}`);
    console.log(`[SSE诊断] taskId: ${taskId}`);
    console.log(`[SSE诊断] lastEventId: ${lastEventId}`);

    try {
      console.log(`[SSE诊断] 开始创建EventSource对象...`);
      const eventSourceInit: EventSourceInit = {};

      // 添加Last-Event-ID头部用于断点续传
      let finalUrl = url;
      if (this.lastEventId) {
        console.log(
          `[SSE诊断] 使用断点续传, Last-Event-ID: ${this.lastEventId}`,
        );
        // 注意：EventSource不支持自定义头部，这里通过URL参数传递
        const separator = url.includes("?") ? "&" : "?";
        finalUrl = `${url}${separator}last_event_id=${encodeURIComponent(this.lastEventId)}`;
        console.log(`[SSE诊断] 断点续传URL: ${finalUrl}`);
      }

      const eventSourceCreateStart = Date.now();
      console.log(
        `[SSE诊断] EventSource构造函数调用 - 时间戳: ${eventSourceCreateStart}`,
      );

      this.eventSource = new EventSource(finalUrl, eventSourceInit);

      const eventSourceCreatedTime = Date.now();
      const createDuration = eventSourceCreatedTime - eventSourceCreateStart;
      console.log(
        `[SSE诊断] EventSource对象创建完成 - 构造函数耗时: ${createDuration}ms, 总耗时: ${eventSourceCreatedTime - connectStartTime}ms`,
      );
      console.log(`[SSE诊断] 创建后readyState: ${this.eventSource.readyState}`);

      // 埋点：记录连接创建
      sseProgressManager.trackEvent("sse_connect_created", {
        taskId,
        url: finalUrl,
        createDuration,
        totalDuration: eventSourceCreatedTime - connectStartTime,
        readyState: this.eventSource.readyState,
        timestamp: eventSourceCreatedTime,
      });

      // 监听连接打开
      this.eventSource.onopen = (event) => {
        const openTime = Date.now();
        const totalDuration = openTime - connectStartTime;

        console.log(
          `[SSE诊断] onopen事件触发 - 时间: ${new Date(openTime).toLocaleTimeString()}`,
        );
        console.log(`[SSE诊断] 连接建立总耗时: ${totalDuration}ms`);
        console.log(
          `[SSE诊断] EventSource.readyState: ${this.eventSource?.readyState}`,
        );
        console.log(`[SSE诊断] EventSource.url: ${this.eventSource?.url}`);
        console.log(`[SSE诊断] 原始event对象:`, event);

        // 添加到连接监控
        SSEMonitor.addConnection(url, this.eventSource!);

        this.reconnectAttempts = 0;

        // 埋点：连接成功
        sseProgressManager.trackEvent("sse_connection_opened", {
          taskId,
          totalDuration,
          readyState: this.eventSource?.readyState,
          url: this.eventSource?.url,
          timestamp: openTime,
          eventType: event.type,
        });

        this.callbacks.onConnected?.({ taskId, timestamp: openTime });
      };

      // 监听消息
      this.eventSource.onmessage = (event) => {
        const msgTime = Date.now();
        const msgDuration = msgTime - connectStartTime;

        console.log(
          `[SSE诊断] onmessage事件触发 - 时间: ${new Date(msgTime).toLocaleTimeString()}`,
        );
        console.log(`[SSE诊断] 从连接开始到收到消息的耗时: ${msgDuration}ms`);
        console.log(`[SSE诊断] 原始消息数据:`, event.data);
        console.log(`[SSE诊断] event.lastEventId: ${event.lastEventId}`);
        console.log(`[SSE诊断] event.type: ${event.type}`);
        console.log(`[SSE诊断] event.origin: ${event.origin}`);

        try {
          const message: BatchProgressMessage = JSON.parse(event.data);
          console.log(
            `[SSE诊断] 消息解析成功 - 类型: ${message.type}, ID: ${message.id}`,
          );

          // 更新lastEventId用于断点续传
          if (event.lastEventId) {
            console.log(
              `[SSE诊断] 更新lastEventId: ${this.lastEventId} -> ${event.lastEventId}`,
            );
            this.lastEventId = event.lastEventId;
          }

          // 埋点：收到消息
          sseProgressManager.trackEvent("sse_message_received", {
            taskId,
            messageType: message.type,
            messageId: message.id,
            duration: msgDuration,
            timestamp: msgTime,
            hasLastEventId: !!event.lastEventId,
          });

          // 去重检查
          if (!MessageDeduplicator.shouldProcess(message)) {
            console.log(`[SSE诊断] 消息被去重过滤: ${message.id}`);
            return;
          }

          this.handleMessage(message);
        } catch (error) {
          console.error(`[SSE诊断] 消息解析失败:`, error);
          console.error(`[SSE诊断] 原始消息内容:`, event.data);

          // 埋点：消息解析失败
          sseProgressManager.trackEvent("sse_message_parse_error", {
            taskId,
            error: error.toString(),
            rawData: event.data,
            duration: msgDuration,
            timestamp: msgTime,
          });

          this.callbacks.onError?.("消息解析失败");
        }
      };

      // 监听错误
      this.eventSource.onerror = (event) => {
        const errorTime = Date.now();
        const errorDuration = errorTime - connectStartTime;

        console.error(
          `[SSE诊断] onerror事件触发 - 时间: ${new Date(errorTime).toLocaleTimeString()}`,
        );
        console.error(`[SSE诊断] 从连接开始到错误的耗时: ${errorDuration}ms`);
        console.error(
          `[SSE诊断] EventSource.readyState: ${this.eventSource?.readyState}`,
        );
        console.error(`[SSE诊断] EventSource.url: ${this.eventSource?.url}`);
        console.error(`[SSE诊断] 原始error event:`, event);
        console.error(`[SSE诊断] 连接是否手动关闭: ${this.isManualClose}`);

        // 埋点：连接错误
        sseProgressManager.trackEvent("sse_connection_error", {
          taskId,
          errorDuration,
          readyState: this.eventSource?.readyState,
          url: this.eventSource?.url,
          timestamp: errorTime,
          eventType: event.type,
          isManualClose: this.isManualClose,
          reconnectAttempts: this.reconnectAttempts,
        });

        this.callbacks.onError?.("SSE连接错误");

        // 非手动关闭时尝试重连
        if (
          !this.isManualClose &&
          this.eventSource?.readyState === EventSource.CLOSED
        ) {
          console.log(
            `[SSE诊断] 准备尝试重连，当前重连次数: ${this.reconnectAttempts}`,
          );
          this.attemptReconnect();
        } else {
          console.log(
            `[SSE诊断] 不尝试重连 - 手动关闭: ${this.isManualClose}, readyState: ${this.eventSource?.readyState}`,
          );
        }
      };
    } catch (error) {
      console.error("[SSE] 创建EventSource失败:", error);
      this.callbacks.onError?.("无法建立SSE连接");
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: BatchProgressMessage): void {
    if (import.meta.env.VITE_ENABLE_DEBUG === "true") {
      console.log("[SSE] 处理消息:", message);
    }

    switch (message.type) {
      case "connected":
        // 连接确认消息，不需要特殊处理
        break;

      case "started":
        this.callbacks.onProgress?.(message);
        break;

      case "progress":
        this.callbacks.onProgress?.(message);
        break;

      case "step":
        this.callbacks.onStep?.(message);
        break;

      case "url_completed":
        this.callbacks.onUrlCompleted?.(message);
        break;

      case "completed":
        this.callbacks.onCompleted?.(message);
        this.disconnect(); // 任务完成，主动断开连接
        break;

      case "error":
        this.callbacks.onError?.(message.error || "处理过程中发生错误");
        break;

      // 新增语义块级别消息处理
      case "chunking_started":
        if (this.callbacks.onChunkingStarted) {
          this.callbacks.onChunkingStarted(message);
        } else {
          console.log("[SSE] chunking_started消息未处理，缺少回调函数");
        }
        break;

      case "chunking_completed":
        if (this.callbacks.onChunkingCompleted) {
          this.callbacks.onChunkingCompleted(message);
        } else {
          console.log("[SSE] chunking_completed消息未处理，缺少回调函数");
        }
        break;

      case "chunks_processing_started":
        if (this.callbacks.onChunksProcessingStarted) {
          this.callbacks.onChunksProcessingStarted(message);
        } else {
          console.log(
            "[SSE] chunks_processing_started消息未处理，缺少回调函数",
          );
        }
        break;

      case "chunk_progress":
        if (this.callbacks.onChunkProgress) {
          this.callbacks.onChunkProgress(message);
        } else {
          console.log("[SSE] chunk_progress消息未处理，缺少回调函数");
        }
        break;

      case "chunks_processing_completed":
        if (this.callbacks.onChunksProcessingCompleted) {
          this.callbacks.onChunksProcessingCompleted(message);
        } else {
          console.log(
            "[SSE] chunks_processing_completed消息未处理，缺少回调函数",
          );
        }
        break;

      case "chunk_completed":
        if (this.callbacks.onChunkCompleted) {
          this.callbacks.onChunkCompleted(message);
        } else {
          console.log("[SSE] chunk_completed消息未处理，缺少回调函数");
        }
        break;

      default:
        if (import.meta.env.VITE_ENABLE_DEBUG === "true") {
          console.warn("[SSE] 未知消息类型:", message.type);
        }
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("[SSE] 重连失败: 达到最大重试次数");
      this.callbacks.onError?.("无法重新连接到服务器");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    if (import.meta.env.VITE_ENABLE_DEBUG === "true") {
      console.log(
        `[SSE] 尝试重连 ${this.reconnectAttempts}/${this.maxReconnectAttempts} 在 ${delay}ms 后`,
      );
    }

    setTimeout(() => {
      if (this.taskId) {
        this.connect(this.taskId, this.callbacks, this.lastEventId);
      }
    }, delay);
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true;

    if (this.eventSource) {
      try {
        this.eventSource.close();
        console.log("[SSE] SSE连接已手动关闭");
      } catch (error) {
        console.error("[SSE] 关闭SSE连接失败:", error);
      }
      this.eventSource = null;
    }

    this.taskId = null;
    this.callbacks = {};
    this.reconnectAttempts = 0;
    this.lastEventId = null;
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    const connected = this.eventSource?.readyState === EventSource.OPEN;
    console.log(
      `[SSE] isConnected() 检查结果: ${connected}, readyState: ${this.eventSource?.readyState}`,
    );
    return connected;
  }

  /**
   * 更新回调函数
   */
  updateCallbacks(callbacks: SSECallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * 获取当前任务ID
   */
  getCurrentTaskId(): string | null {
    return this.taskId;
  }

  /**
   * 获取最后事件ID（用于断点续传）
   */
  getLastEventId(): string | null {
    return this.lastEventId;
  }

  /**
   * 获取活跃连接数
   */
  static getActiveConnectionCount(): number {
    return SSEMonitor.activeConnections.size;
  }
}

// SSE预连接管理器 - 带埋点监控
export class SSEProgressManager {
  private eventSource: EventSource | null = null;
  private connectionState:
    | "disconnected"
    | "connecting"
    | "connected"
    | "failed" = "disconnected";
  private connectionStartTime: number = 0;
  private reconnectAttempts: number = 0;
  private currentTaskId: string | null = null;

  // 埋点数据收集
  private metrics = {
    connectionAttempts: 0,
    connectionSuccessTime: 0,
    connectionFailures: 0,
    messageCount: 0,
    lastMessageTime: 0,
    reconnectCount: 0,
  };

  // 预连接方法
  preConnect(taskId?: string) {
    console.log("[SSE预连接] 开始预连接");
    this.trackEvent("sse_preconnect_start", { taskId });

    this.connectionState = "connecting";
    this.connectionStartTime = Date.now();
    this.metrics.connectionAttempts++;

    // 使用通用端点或预连接端点
    const baseUrl =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const url = taskId
      ? `${baseUrl}/api/v1/progress/${taskId}`
      : `${baseUrl}/api/v1/progress/preconnect`; // 预连接端点

    this.eventSource = new EventSource(url);

    this.setupEventHandlers();
  }

  private setupEventHandlers() {
    if (!this.eventSource) return;

    // 连接成功
    this.eventSource.onopen = () => {
      const connectTime = Date.now() - this.connectionStartTime;
      this.connectionState = "connected";
      this.metrics.connectionSuccessTime = connectTime;

      this.trackEvent("sse_connection_success", {
        connectTime,
        attempts: this.metrics.connectionAttempts,
        reconnects: this.metrics.reconnectCount,
      });

      console.log(`[SSE预连接] 连接成功，耗时: ${connectTime}ms`);
    };

    // 收到消息
    this.eventSource.onmessage = (event) => {
      this.metrics.messageCount++;
      this.metrics.lastMessageTime = Date.now();

      try {
        const data = JSON.parse(event.data);
        this.trackEvent("sse_message_received", {
          messageCount: this.metrics.messageCount,
          timeSinceLastMessage: Date.now() - this.metrics.lastMessageTime,
          messageType: data.type,
        });
      } catch (e) {
        // 静默处理解析错误
      }
    };

    // 连接错误
    this.eventSource.onerror = (error) => {
      this.metrics.connectionFailures++;
      this.connectionState = "failed";

      this.trackEvent("sse_connection_error", {
        error: error.toString(),
        attempts: this.metrics.connectionAttempts,
        failures: this.metrics.connectionFailures,
      });

      // 自动重连逻辑
      if (this.reconnectAttempts < 3) {
        this.reconnectAttempts++;
        setTimeout(() => this.reconnect(), 1000 * this.reconnectAttempts);
      }
    };
  }

  private reconnect() {
    this.metrics.reconnectCount++;
    this.trackEvent("sse_reconnect_attempt", {
      attempt: this.reconnectAttempts,
      totalReconnects: this.metrics.reconnectCount,
    });

    this.disconnect();
    this.preConnect();
  }

  // 切换到特定任务
  switchToTask(taskId: string) {
    if (this.connectionState === "connected") {
      this.trackEvent("sse_task_switch", {
        fromTask: this.currentTaskId,
        toTask: taskId,
        connectionAge: Date.now() - this.connectionStartTime,
      });

      // 可以发送切换命令到服务器（如果需要）
      // this.sendCommand('switch_task', { taskId });
    } else {
      // 如果未连接，重新连接到特定任务
      this.disconnect();
      this.preConnect(taskId);
    }
    this.currentTaskId = taskId;
  }

  // 断开连接
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.connectionState = "disconnected";
    this.currentTaskId = null;
  }

  // 埋点方法
  public trackEvent(eventName: string, data: any = {}) {
    const eventData = {
      timestamp: Date.now(),
      sessionId: this.getSessionId(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      connectionState: this.connectionState,
      ...data,
    };

    // 发送到监控系统
    this.sendToMonitoring(eventName, eventData);

    // 控制台日志（开发环境）
    if (import.meta.env.DEV) {
      console.log(`[埋点] ${eventName}:`, eventData);
    }
  }

  private sendToMonitoring(eventName: string, data: any) {
    // 可以发送到多种监控系统
    const baseUrl =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    try {
      // 1. 自定义监控API
      fetch(`${baseUrl}/api/monitoring/sse-events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: eventName, data }),
      }).catch(() => {}); // 静默失败

      // 2. Google Analytics / 其他分析工具
      if ((window as any).gtag) {
        (window as any).gtag("event", eventName, data);
      }

      // 3. Sentry / 错误监控
      if ((window as any).Sentry) {
        (window as any).Sentry.captureMessage(`SSE: ${eventName}`, {
          level: "info",
          extra: data,
        });
      }
    } catch (e) {
      // 静默失败，不影响主流程
    }
  }

  // 获取会话ID
  private getSessionId(): string {
    let sessionId = localStorage.getItem("sse_session_id");
    if (!sessionId) {
      sessionId = `sse_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem("sse_session_id", sessionId);
    }
    return sessionId;
  }

  // 健康检查
  getHealthStatus() {
    const now = Date.now();
    return {
      state: this.connectionState,
      connectionAge: now - this.connectionStartTime,
      timeSinceLastMessage: now - this.metrics.lastMessageTime,
      metrics: { ...this.metrics },
      reconnectAttempts: this.reconnectAttempts,
    };
  }
}

// 创建单例实例
export const sseService = new SSEService();
export const sseProgressManager = new SSEProgressManager();

export default sseService;
