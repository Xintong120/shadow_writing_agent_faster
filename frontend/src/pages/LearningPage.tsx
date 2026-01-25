// frontend/src/pages/LearningPage.tsx
// 学习页面 - 实时显示Shadow Writing学习卡片

import { useState, useEffect, useRef } from "react";
import { ArrowLeft, BookOpen, Sparkles, Target } from "lucide-react";
import LearningCard from "@/components/LearningCard";
import { LearningItem } from "@/types/learning";
import { sseService } from "@/services/progress";
import type { BatchProgressMessage } from "@/types";

interface LearningPageProps {
  taskId?: string | null;
  tedTitle?: string;
  tedSpeaker?: string;
  lastEventId?: string | null; // 新增：从ProcessingPage传递的最后事件ID
  receivedChunks?: any[]; // 新增：从ProcessingPage传递的已接收chunks
  onBack?: () => void;
}

const LearningPage = ({
  taskId,
  tedTitle = "TED Learning Session",
  tedSpeaker = "Unknown Speaker",
  lastEventId,
  receivedChunks = [],
}: LearningPageProps) => {
  const [learningItems, setLearningItems] = useState<LearningItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const hasSetInitialItems = useRef(false);

  // 将后端数据转换为前端LearningItem格式
  const convertToLearningItem = (
    chunkData: any,
    chunkId: number,
  ): LearningItem => {
    const { original, imitation, map } = chunkData;

    // 将map字典转换为mapping数组
    const mapping = Object.entries(map || {}).flatMap(
      ([from, toList]: [string, any]) =>
        Array.isArray(toList) ? toList.map((to: string) => ({ from, to })) : [],
    );

    return {
      id: chunkId,
      original,
      mimic: imitation, // imitation对应前端的mimic
      mapping,
    };
  };

  // 设置SSE监听 - 使用SSEService进行断点续传
  useEffect(() => {
    if (!taskId) {
      setIsLoading(false);
      return;
    }

    console.log("[LearningPage] 组件初始化");
    console.log("[LearningPage] taskId:", taskId);
    console.log("[LearningPage] lastEventId:", lastEventId);
    console.log("[LearningPage] receivedChunks 长度:", receivedChunks.length);
    console.log(
      "[LearningPage] receivedChunks 详情:",
      receivedChunks.map((chunk, index) => ({
        index,
        chunk_id: chunk.chunk_id,
        type: chunk.type,
        hasResult: !!chunk.result,
        resultLength: chunk.result ? chunk.result.length : 0,
        timestamp: chunk.timestamp,
      })),
    );

    // 首先将已接收的chunks转换为learningItems（只设置一次）
    if (!hasSetInitialItems.current && receivedChunks.length > 0) {
      const initialItems = receivedChunks.map((chunk) =>
        convertToLearningItem(chunk.result, chunk.chunk_id || 0),
      );
      setLearningItems(initialItems);
      hasSetInitialItems.current = true;
      console.log(
        "[LearningPage] 初始化时设置learningItems数量:",
        initialItems.length,
        "来自ProcessingPage的chunks",
      );
      console.log(
        "[LearningPage] 初始learningItems详情:",
        initialItems.map((item, index) => ({
          index,
          id: item.id,
          hasOriginal: !!item.original,
          hasMimic: !!item.mimic,
          mappingCount: item.mapping?.length || 0,
        })),
      );
    }

    // SSE回调函数
    const sseCallbacks = {
      onConnected: () => {
        console.log("[LearningPage] SSE connected");
        setConnectionStatus("connected");
        setIsLoading(false);
      },

      onChunkCompleted: (data: BatchProgressMessage) => {
        const chunk_id = data.chunk_id;
        const original_timestamp = data.timestamp;
        const receive_time = Date.now();

        console.log("[LearningPage] Received chunk:", chunk_id);

        // 增强调试日志 - 记录learningItems更新的详细时间信息
        if (original_timestamp) {
          // 处理时间戳类型 - 后端可能发送秒或毫秒
          let original_date: Date;
          if (typeof original_timestamp === "number") {
            if (original_timestamp > 10000000000) {
              // 已经是毫秒
              original_date = new Date(original_timestamp);
            } else {
              // 是秒，需要转换为毫秒
              original_date = new Date(original_timestamp * 1000);
            }
          } else {
            // 字符串时间戳
            original_date = new Date(original_timestamp);
          }

          const delay_from_completion =
            (receive_time - original_date.getTime()) / 1000; // 转换为秒

          console.log(
            `[CHUNK_TRACKING] LearningPage处理Chunk ${chunk_id} 详情:`,
          );
          console.log(
            `  [CHUNK_TRACKING] 后端原始完成时间: ${original_date.toLocaleTimeString()}`,
          );
          console.log(
            `  [CHUNK_TRACKING] LearningPage接收时间: ${new Date(receive_time).toLocaleTimeString()}`,
          );
          console.log(
            `  [CHUNK_TRACKING] 从chunk完成到LearningPage接收总延迟: ${delay_from_completion.toFixed(6)}秒`,
          );
          console.log(
            `  [CHUNK_TRACKING] 当前learningItems数量: ${learningItems.length} -> ${learningItems.length + 1}`,
          );
        }

        const learningItem = convertToLearningItem(
          data.result,
          data.chunk_id || 0,
        );
        setLearningItems((prev) => [...prev, learningItem]);
      },

      onCompleted: (data: BatchProgressMessage) => {
        console.log("[LearningPage] Processing completed");
        console.log(
          "[LearningPage] 总共接收到的chunks数量:",
          learningItems.length,
        );
        setConnectionStatus("connected"); // 保持连接状态显示
      },

      onError: (errorMsg: string) => {
        console.error("[LearningPage] SSE error:", errorMsg);
        setConnectionStatus("disconnected");
        setIsLoading(false);
      },

      onClose: () => {
        console.log("[LearningPage] SSE connection closed");
        setConnectionStatus("disconnected");
      },
    };

    // 连接SSE，使用断点续传
    sseService.connect(taskId, sseCallbacks, lastEventId);

    // 清理函数
    return () => {
      console.log("[LearningPage] Disconnecting SSE");
      sseService.disconnect();
    };
  }, [taskId, lastEventId, receivedChunks]);

  // 如果没有任务ID，显示错误状态
  if (!taskId) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📚</div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
            No Learning Session
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mb-4">
            Please start a TED processing task first.
          </p>
          <button
            onClick={() => window.history.back()}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => window.history.back()}
                className="p-2 text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                title="Back to Home"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                  <BookOpen size={24} className="text-indigo-600" />
                  {tedTitle}
                </h1>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  by {tedSpeaker}
                </p>
              </div>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  connectionStatus === "connected"
                    ? "bg-green-500"
                    : connectionStatus === "connecting"
                      ? "bg-yellow-500"
                      : "bg-red-500"
                }`}
              />
              <span className="text-sm text-slate-600 dark:text-slate-400 capitalize">
                {connectionStatus}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="mb-8 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-indigo-600 mb-1">
                {learningItems.length}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">
                Learning Cards
              </div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-emerald-600 mb-1 flex items-center justify-center gap-1">
                <Sparkles size={20} />
                {learningItems.length > 0 ? "Active" : "Waiting"}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">
                Session Status
              </div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600 mb-1 flex items-center justify-center gap-1">
                <Target size={20} />
                {learningItems.length}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">
                Completed Chunks
              </div>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && learningItems.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-flex items-center gap-3 px-6 py-3 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 rounded-lg">
              <div className="animate-spin w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full"></div>
              <span>Connecting to learning session...</span>
            </div>
          </div>
        )}

        {/* Learning Cards */}
        {learningItems.length > 0 && (
          <div className="space-y-6">
            {learningItems.map((item) => (
              <LearningCard key={item.id} data={item} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && learningItems.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📝</div>
            <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100 mb-2">
              Waiting for Learning Content
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Shadow writing results will appear here as they are generated.
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-lg">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-pulse"></div>
              <span>Listening for updates...</span>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-slate-500 dark:text-slate-400">
          <p>Real-time Shadow Writing Learning Session</p>
          <p className="mt-1">
            Cards update automatically as processing completes
          </p>
        </footer>
      </main>
    </div>
  );
};

export default LearningPage;
