// frontend/src/pages/ProcessingPage.tsx
// 处理中页面 - 显示实时进度条和处理状态（通过WebSocket连接后端）

import { useState, useEffect, useRef, useCallback, memo } from "react";
import { toast } from "sonner";
import { sseService, sseProgressManager } from "@/services/progress";
import { api } from "@/services/api";
import type { BatchProgressMessage } from "@/types";

let renderCount = 0;
let lastProgressUpdate = 0;
let lastLogUpdate = 0;
const THROTTLE_MS = 300;

interface ProcessingPageProps {
  taskId?: string | null;
  onFinish?: () => void;
  onFirstChunkCompleted?: (taskId: string, receivedChunks: any[]) => void;
}

interface ProgressCircleProps {
  progress: number;
  isConnected: boolean;
}

const ProgressCircle = memo(function ProgressCircle({ progress, isConnected }: ProgressCircleProps) {
  const circleRef = useRef<SVGCircleElement>(null);
  const percentRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (circleRef.current) {
      const offset = 440 - (440 * progress) / 100;
      circleRef.current.style.strokeDashoffset = String(offset);
    }
    if (percentRef.current) {
      percentRef.current.textContent = `${Math.round(progress)}%`;
    }
  }, [progress]);

  return (
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
          ref={circleRef}
          cx="80"
          cy="80"
          r="70"
          stroke="#6366f1"
          strokeWidth="8"
          fill="none"
          strokeDasharray={440}
          strokeDashoffset={440}
          style={{ transition: "stroke-dashoffset 300ms ease-out" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span ref={percentRef} className="text-3xl font-bold text-slate-800 dark:text-white">
          {Math.round(progress)}%
        </span>
        <div
          className={`w-3 h-3 rounded-full mt-2 ${isConnected ? "bg-green-500" : "bg-yellow-500 animate-pulse"}`}
        />
      </div>
    </div>
  );
});

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

  useEffect(() => {
    console.log("[ProcessingPage] 开始SSE预连接");

    sseProgressManager.preConnect();

    const healthCheck = setInterval(() => {
      const health = sseProgressManager.getHealthStatus();

      if (health.state === "connected") {
        setSseConnectionStatus("预连接就绪");
        console.log("[ProcessingPage] SSE预连接成功");
      } else if (health.state === "failed") {
        setSseConnectionStatus("预连接失败");
        console.warn("[ProcessingPage] SSE预连接失败，将使用标准连接");
      }

      sseProgressManager.trackEvent("sse_health_check", health);
    }, 2000);

    return () => {
      clearInterval(healthCheck);
    };
  }, []);

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

    addLog("正在连接服务器...");

    const sseCallbacks = {
      onConnected: () => {
        console.log("[ProcessingPage] SSE连接确认");
        setIsConnected(true);
        setSseConnectionStatus("已连接");
        setCurrentStep("开始处理...");
        addLog("已连接到服务器");
      },

      onProgress: (data: BatchProgressMessage) => {
        const now = Date.now();
        if (now - lastProgressUpdate < THROTTLE_MS) return;
        lastProgressUpdate = now;
        console.log("[ProcessingPage] 收到进度消息:", data);

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

      onChunkCompleted: (data: BatchProgressMessage) => {
        console.log("[ProcessingPage] 收到chunk完成消息:", data);
        console.log(
          "[ProcessingPage] 当前receivedChunks长度:",
          receivedChunks.length,
        );

        receivedChunksRef.current = [...receivedChunksRef.current, data];
        setReceivedChunks(receivedChunksRef.current);

        console.log("[ProcessingPage] 新增chunk详情:", {
          chunk_id: data.chunk_id,
          type: data.type,
          hasResult: !!data.result,
          timestamp: data.timestamp,
        });

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

          setTimeout(() => {
            console.log("[ProcessingPage] 执行跳转，调用onFirstChunkCompleted");
            onFirstChunkCompleted(taskId, receivedChunksRef.current);
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

    const isAlreadyConnected = sseService.isConnected();
    const currentTaskId = sseService.getCurrentTaskId();

    if (isAlreadyConnected && currentTaskId === taskId) {
      console.log("[ProcessingPage] SSE已连接且taskId匹配，使用现有连接");
      sseService.updateCallbacks(sseCallbacks);
      setIsConnected(true);
      setSseConnectionStatus("已连接");
    } else {
      if (isAlreadyConnected) {
        console.log("[ProcessingPage] 断开现有SSE连接");
        sseService.disconnect();
      }

      console.log("[ProcessingPage] 建立新的SSE连接");
      sseService.connect(taskId, sseCallbacks);
    }

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
      }
    };

    checkTaskStatus();

    return () => {
      console.log("[ProcessingPage] 组件卸载，保持SSE连接");
    };
  }, [taskId]);

  const addLog = useCallback((message: string) => {
    const now = Date.now();
    if (now - lastLogUpdate < THROTTLE_MS) return;
    lastLogUpdate = now;
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${timestamp}] ${message}`, ...prev].slice(0, 10));
  }, []);

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
        <ProgressCircle progress={progress} isConnected={isConnected} />
        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
          正在生成学习内容
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mb-4">{currentStep}</p>
        <div className="text-sm text-slate-400 space-y-1">
          <div>连接状态: {sseConnectionStatus}</div>
          {sseError && <div className="text-red-400">错误: {sseError}</div>}
        </div>
      </div>

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

      <div className="text-center mt-6">
        <p className="text-xs text-slate-400">任务ID: {taskId}</p>
      </div>
    </div>
  );
};

export default ProcessingPage;
