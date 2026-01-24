// frontend/src/pages/LearningPage.tsx
// 学习页面 - 实时显示Shadow Writing学习卡片

import { useState, useEffect, useRef } from "react";
import { ArrowLeft, BookOpen, Sparkles, Target } from "lucide-react";
import LearningCard from "@/components/LearningCard";
import { LearningItem } from "@/types/learning";

// SSE消息类型
interface ChunkCompletedMessage {
  type: "chunk_completed";
  chunk_id: number;
  result: {
    original: string;
    imitation: string;
    map: Record<string, string[]>;
    paragraph: string;
    quality_score: number;
  };
  timestamp: number;
}

interface LearningPageProps {
  taskId?: string | null;
  tedTitle?: string;
  tedSpeaker?: string;
  onBack?: () => void;
}

const LearningPage = ({
  taskId,
  tedTitle = "TED Learning Session",
  tedSpeaker = "Unknown Speaker",
}: LearningPageProps) => {
  const [learningItems, setLearningItems] = useState<LearningItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");
  const eventSourceRef = useRef<EventSource | null>(null);

  // 将后端数据转换为前端LearningItem格式
  const convertToLearningItem = (
    chunkData: ChunkCompletedMessage["result"],
    chunkId: number,
  ): LearningItem => {
    const { original, imitation, map } = chunkData;

    // 将map字典转换为mapping数组
    const mapping = Object.entries(map).flatMap(([from, toList]) =>
      toList.map((to) => ({ from, to })),
    );

    return {
      id: chunkId,
      original,
      mimic: imitation, // imitation对应前端的mimic
      mapping,
    };
  };

  // 设置SSE监听
  useEffect(() => {
    if (!taskId) {
      setIsLoading(false);
      return;
    }

    const setupSSE = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(
        `http://localhost:8000/api/v1/progress/${taskId}`,
      );
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log("[SSE] Learning page connected");
        setConnectionStatus("connected");
        setIsLoading(false);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ChunkCompletedMessage;

          if (data.type === "chunk_completed") {
            console.log("[SSE] Received chunk:", data.chunk_id);

            const learningItem = convertToLearningItem(
              data.result,
              data.chunk_id,
            );
            setLearningItems((prev) => [...prev, learningItem]);
          }
        } catch (error) {
          console.error("[SSE] Parse error:", error);
        }
      };

      eventSource.onerror = () => {
        console.error("[SSE] Connection error");
        setConnectionStatus("disconnected");
        setIsLoading(false);

        // 自动重连
        setTimeout(() => {
          if (eventSource.readyState === EventSource.CLOSED) {
            setupSSE();
          }
        }, 3000);
      };
    };

    setupSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [taskId]);

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
