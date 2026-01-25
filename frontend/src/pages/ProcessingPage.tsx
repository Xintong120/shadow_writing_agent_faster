// frontend/src/pages/ProcessingPage.tsx
// 处理中页面 - 显示实时进度条和处理状态（通过WebSocket连接后端）

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { sseService, sseProgressManager } from "@/services/progress";
import { api } from "@/services/api";
import type { BatchProgressMessage } from "@/types";

interface ProcessingPageProps {
  taskId?: string | null;
  onFinish?: () => void;
  onFirstChunkCompleted?: (taskId: string, receivedChunks: any[]) => void; // 新增：第一个chunk完成时的回调，传递已接收的chunks
}

let renderCount = 0;

const ProcessingPage = ({
  taskId,
  onFinish,
  onFirstChunkCompleted,
}: ProcessingPageProps) => {
  renderCount++;
  const currentTime = Date.now();
  console.log(
    `[ProcessingPage] 组件渲染 #${renderCount} - taskId: ${taskId} 时间: ${new Date(currentTime).toLocaleTimeString()}`,
  );

  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState<string>("连接服务器...");
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useFallbackProgress, setUseFallbackProgress] = useState(false);
  const [lastProgressUpdate, setLastProgressUpdate] = useState(Date.now());
  const [connectionTimeout, setConnectionTimeout] =
    useState<NodeJS.Timeout | null>(null);
  const [sseConnectionStatus, setSseConnectionStatus] =
    useState<string>("预连接中...");
  const [sseError, setSseError] = useState<string | null>(null);
  const [hasTriggeredFirstChunkJump, setHasTriggeredFirstChunkJump] =
    useState(false);
  const hasTriggeredRef = useRef(false);
  const [receivedChunks, setReceivedChunks] = useState<any[]>([]);
  const receivedChunksRef = useRef<any[]>([]);

  // 预连接SSE - 页面加载时执行
  useEffect(() => {
    console.log("[ProcessingPage] 开始SSE预连接");

    // 预连接到通用端点
    sseProgressManager.preConnect();

    // 定期检查预连接状态
    const healthCheck = setInterval(() => {
      const health = sseProgressManager.getHealthStatus();

      if (health.state === "connected") {
        setSseConnectionStatus("预连接就绪");
        console.log("[ProcessingPage] SSE预连接成功");
      } else if (health.state === "failed") {
        setSseConnectionStatus("预连接失败");
        console.warn("[ProcessingPage] SSE预连接失败，将使用标准连接");
      }

      // 埋点：定期健康检查
      sseProgressManager.trackEvent("sse_health_check", health);
    }, 2000); // 每2秒检查一次

    return () => {
      clearInterval(healthCheck);
      // 注意：不要在这里断开预连接，让它保持活跃
    };
  }, []); // 只在组件挂载时执行一次

  useEffect(() => {
    const useEffectStartTime = Date.now();
    console.log(
      `[ProcessingPage] useEffect开始执行 - 时间: ${new Date(useEffectStartTime).toLocaleTimeString()}, taskId:`,
      taskId,
    );

    if (!taskId) {
      console.error("[ProcessingPage] taskId缺失");
      setError("任务ID缺失");
      toast.error("任务ID缺失，请重新开始");
      setTimeout(() => onFinish?.(), 1000);
      return;
    }

    console.log("[ProcessingPage] 开始SSE连接和API检查");

    // 添加初始日志
    addLog("正在连接服务器...");

    // SSE连接回调函数
    const sseCallbacks = {
      onConnected: () => {
        console.log("[ProcessingPage] SSE连接确认");
        setIsConnected(true);
        setSseConnectionStatus("已连接");
        setCurrentStep("开始处理...");
        addLog("已连接到服务器");
      },

      onProgress: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到进度消息:", data);
        setLastProgressUpdate(Date.now());

        if (data.progress !== undefined) {
          setProgress(data.progress);
          addLog(`进度更新: ${data.progress}%`);
        } else if (data.current !== undefined && data.total !== undefined) {
          const percentage = Math.round((data.current / data.total) * 100);
          setProgress(percentage);
          addLog(`处理进度: ${data.current}/${data.total} (${percentage}%)`);
        }

        if (data.url) {
          addLog(`当前处理: ${data.url}`);
        }
      },

      onStep: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到步骤消息:", data);
        if (data.step) {
          setCurrentStep(data.step);
          addLog(`执行步骤: ${data.step}`);
        }
        if (data.message) addLog(data.message);
      },

      // 新增语义块级别进度消息处理
      onChunkingStarted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到分块开始消息:", data);
        setCurrentStep("语义分块处理");
        addLog(`开始语义分块: 文本长度 ${data.text_length} 字符`);
      },

      onChunkingCompleted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到分块完成消息:", data);
        addLog(`语义分块完成: 生成 ${data.total_chunks} 个语义块`);
        if (data.chunk_sizes) {
          addLog(`各块大小: ${data.chunk_sizes.join(", ")} 字符`);
        }
      },

      onChunksProcessingStarted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到并行处理开始消息:", data);
        setCurrentStep("并行处理语义块");
        addLog(`开始并行处理 ${data.total_chunks} 个语义块`);
      },

      onChunkProgress: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到语义块进度消息:", data);
        if (data.stage === "shadow_writing") {
          addLog(
            `处理语义块 ${data.current_chunk}/${data.total_chunks}: 生成Shadow Writing`,
          );
        }
      },

      onChunksProcessingCompleted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到并行处理完成消息:", data);
        addLog(`所有 ${data.total_chunks} 个语义块处理完成`);
      },

      // 新增：监听第一个chunk完成消息
      onChunkCompleted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到chunk完成消息:", data);
        console.log(
          "[ProcessingPage] 当前receivedChunks长度:",
          receivedChunks.length,
        );

        // 使用ref确保同步更新
        receivedChunksRef.current = [...receivedChunksRef.current, data];
        setReceivedChunks(receivedChunksRef.current);

        console.log("[ProcessingPage] 新增chunk详情:", {
          chunk_id: data.chunk_id,
          type: data.type,
          hasResult: !!data.result,
          timestamp: data.timestamp,
        });

        // 只在第一次收到chunk完成消息时触发跳转
        if (!hasTriggeredRef.current && taskId && onFirstChunkCompleted) {
          console.log("[ProcessingPage] 触发第一次chunk完成跳转");
          console.log(
            "[ProcessingPage] 传递的chunks数量:",
            receivedChunksRef.current.length,
          );
          console.log(
            "[ProcessingPage] 最终传递的chunks数组:",
            receivedChunksRef.current,
          );
          hasTriggeredRef.current = true;
          setHasTriggeredFirstChunkJump(true);
          addLog("第一个学习卡片已生成，开始学习模式！");
          setCurrentStep("跳转到学习页面...");

          // 延迟一点时间让用户看到消息，然后跳转
          setTimeout(() => {
            console.log("[ProcessingPage] 执行跳转，调用onFirstChunkCompleted");
            onFirstChunkCompleted(taskId, receivedChunksRef.current); // 传递完整的ref数组
          }, 1500);
        }
      },

      onUrlCompleted: (data: BatchProgressMessage) => {
        if (data.url) addLog(`完成处理: ${data.url}`);
      },

      onCompleted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到完成消息:", data);
        console.log("[ProcessingPage] onFinish存在:", !!onFinish);
        setProgress(100);
        setCurrentStep("处理完成");
        addLog("所有任务处理完成！");

        if (data.successful !== undefined && data.failed !== undefined) {
          addLog(
            `处理结果: 成功 ${data.successful} 个, 失败 ${data.failed} 个`,
          );
        }

        console.log("[ProcessingPage] 准备调用onFinish，1秒后跳转");
        setTimeout(() => {
          console.log("[ProcessingPage] 执行onFinish调用");
          onFinish?.();
        }, 1000);
      },

      onError: (errorMsg: string) => {
        console.error("[ProcessingPage] SSE错误:", errorMsg);
        setSseError(errorMsg);
        setError(errorMsg);
        addLog(`错误: ${errorMsg}`);
        toast.error(`处理错误: ${errorMsg}`);
      },

      onClose: (code: number, reason: string) => {
        console.log("[ProcessingPage] SSE连接关闭");
        setIsConnected(false);
        if (code !== 1000) {
          addLog(`连接断开: ${reason}`);
        }
      },
    };

    // 检查是否已有SSE连接
    const isAlreadyConnected = sseService.isConnected();
    const currentTaskId = sseService.getCurrentTaskId();

    if (isAlreadyConnected && currentTaskId === taskId) {
      console.log("[ProcessingPage] SSE已连接且taskId匹配，使用现有连接");
      sseService.updateCallbacks(sseCallbacks);
      setIsConnected(true);
      setSseConnectionStatus("已连接");
    } else {
      // 断开现有连接，建立新连接
      if (isAlreadyConnected) {
        console.log("[ProcessingPage] 断开现有SSE连接");
        sseService.disconnect();
      }

      console.log("[ProcessingPage] 建立新的SSE连接");
      sseService.connect(taskId, sseCallbacks);
    }

    // 并行检查任务状态
    const checkTaskStatus = async () => {
      try {
        const task = await api.getTaskStatus(taskId);
        if (task.status === "completed") {
          setProgress(100);
          setCurrentStep("处理完成");
          addLog("处理已完成");
          setTimeout(() => onFinish?.(), 1000);
        }
      } catch (error) {
        console.log(
          "[ProcessingPage] 任务状态检查失败（可能因API key冷却超时）:",
          error,
        );
        // 不显示错误，继续等待SSE消息
      }
    };

    checkTaskStatus();

    // 清理函数
    return () => {
      // 页面卸载时不断开连接，让SSE服务管理连接生命周期
      console.log("[ProcessingPage] 组件卸载，保持SSE连接");
    };
  }, [taskId]);

  // 添加日志的辅助函数
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${timestamp}] ${message}`, ...prev].slice(0, 10)); // 保留最近10条日志
  };

  // 如果有错误，显示错误状态
  if (error) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="text-red-500 mb-4">⚠️ 处理出错</div>
        <p className="text-slate-600 dark:text-slate-400 mb-4">{error}</p>
        <button
          onClick={() => onFinish?.()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg"
        >
          返回首页
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-20">
      <div className="text-center mb-8">
        <div className="relative w-40 h-40 mx-auto mb-8">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="#e2e8f0"
              strokeWidth="8"
              fill="none"
              className="dark:stroke-slate-700"
            />
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="#6366f1"
              strokeWidth="8"
              fill="none"
              strokeDasharray={440}
              strokeDashoffset={440 - (440 * progress) / 100}
              className="transition-all duration-200 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center flex-col">
            <span className="text-3xl font-bold text-slate-800 dark:text-white">
              {Math.round(progress)}%
            </span>
            <div
              className={`w-3 h-3 rounded-full mt-2 ${isConnected ? "bg-green-500" : "bg-yellow-500 animate-pulse"}`}
            />
          </div>
        </div>
        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
          正在生成学习内容
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mb-4">{currentStep}</p>
        <div className="text-sm text-slate-400 space-y-1">
          <div>连接状态: {sseConnectionStatus}</div>
          {sseError && <div className="text-red-400">错误: {sseError}</div>}
        </div>
      </div>

      {/* 日志区域 */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 max-h-64 overflow-y-auto">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
          处理日志
        </h4>
        <div className="space-y-1">
          {logs.length === 0 ? (
            <p className="text-slate-500 text-sm">等待日志...</p>
          ) : (
            logs.map((log, index) => (
              <p
                key={index}
                className="text-xs text-slate-600 dark:text-slate-400 font-mono"
              >
                {log}
              </p>
            ))
          )}
        </div>
      </div>

      {/* 任务ID显示 */}
      <div className="text-center mt-6">
        <p className="text-xs text-slate-400">任务ID: {taskId}</p>
      </div>
    </div>
  );
};

export default ProcessingPage;
