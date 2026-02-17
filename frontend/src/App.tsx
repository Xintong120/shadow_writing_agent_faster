import { useState, useEffect, useCallback, useRef } from "react";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { TaskProvider } from "@/contexts/TaskContext";
import { Toaster } from "sonner";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/services/queryClient";
import { useQueryClient } from "@tanstack/react-query";

// 移除Lazy loading，直接导入组件
import LoginPage from "@/pages/LoginPage";
import SearchPage from "@/pages/SearchPage";
import ProcessingPage from "@/pages/ProcessingPage";
import PreviewPage from "@/pages/PreviewPage";
import LearningSessionPage from "@/pages/LearningSessionPage";
import HistoryPage from "@/pages/HistoryPage";
import SettingsPage from "@/pages/SettingsPage";
import StatsPage from "@/pages/StatsPage";
import DownloadsPage from "@/pages/DownloadsPage";
import VocabPage from "@/components/VocabPage";
import DebateSelectPage from "@/pages/DebateSelectPage";
import DebatePage from "@/pages/DebatePage";
import Navigation from "@/components/Navigation";
import { ActiveTab } from "@/types/navigation";
import { useVocab } from "@/hooks/useVocab";
import { TedTalk } from "@/types/ted";
import { LearningStatus } from "@/types/history";
import { taskHistoryStorage } from "@/services/taskHistoryStorage";
import { sseService } from "@/services/progress";
import { getHistoryList, updateHistoryStatus } from "@/services/downloadApi";
import LearningContext, { HistoryRecord, useLearning } from "@/contexts/LearningContext";
import dJSON from "dirty-json";

// Auth Wrapper Component with State Machine
const AuthWrapper = () => {
  const { authStatus, login, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const { vocabList, loading, deleteWord, refresh: refreshVocab } = useVocab()
  const [appState, setAppState] = useState<
    "idle" | "processing" | "preview" | "learning" | "learning_cards" | "debate_select" | "debate"
  >("idle");
  const [processedTalks, setProcessedTalks] = useState<TedTalk[]>([]);
  const [currentLearningTalk, setCurrentLearningTalk] =
    useState<TedTalk | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const [receivedChunks, setReceivedChunks] = useState<any[]>([]);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const hasJumpedToLearningCards = useRef(false);
  const [historyInitialTab, setHistoryInitialTab] =
    useState<LearningStatus>("todo");
  const [tedTitle, setTedTitle] = useState("");
  const [tedSpeaker, setTedSpeaker] = useState("");

  // Apply dark mode to document element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDarkMode]);

  // LearningContext Actions
  const queryClient = useQueryClient()

  const startLearningFromRecord = useCallback(async (record: HistoryRecord & { result?: { chunks?: any[] } }) => {
    console.log('[App] startLearningFromRecord:', record.ted_title);

    // 如果 record 有 chunks，直接使用
    let chunks = record.result?.chunks || [];

    // 如果没有 chunks，尝试从 API 获取
    if (chunks.length === 0 && record.task_id) {
      console.log('[App] 尝试从 API 获取 chunks...');
      try {
        const historyList = await getHistoryList(50, 0);
        const fullRecord = historyList.find(h => h.task_id === record.task_id);
        if (fullRecord?.result?.chunks) {
          chunks = fullRecord.result.chunks;
          console.log('[App] 从 API 获取到 chunks:', chunks.length);
        }
      } catch (error) {
        console.error('[App] 获取 chunks 失败:', error);
      }
    }

    // 更新状态为 in_progress（学习中）
    if (record.task_id) {
      await updateHistoryStatus(record.task_id, 'in_progress');
      queryClient.invalidateQueries({ queryKey: ['history'] });
      console.log('[App] 更新状态为 in_progress');
    }

    setCurrentTaskId(record.task_id);
    setReceivedChunks(chunks);
    setTedTitle(record.ted_title || '');
    setTedSpeaker(record.ted_speaker || '');
    setActiveTab("chat");
    setAppState("learning_cards");
  }, []);

  const clearLearning = useCallback(() => {
    console.log('[App] clearLearning');
    setCurrentTaskId(null);
    setReceivedChunks([]);
    setAppState("idle");
  }, []);

  // 提供 LearningContext
  const learningContextValue = {
    view: appState === "learning_cards" ? "learning" as const : "idle" as const,
    taskId: currentTaskId,
    chunks: receivedChunks,
    tedTitle: tedTitle,
    tedSpeaker: tedSpeaker,
    startLearningFromRecord,
    clearLearning,
  };

  const handleStartProcessing = (talks: TedTalk[], taskId?: string) => {
    console.log("开始处理演讲:", talks, "taskId:", taskId);

    if (taskId) {
      const savedIds = JSON.parse(localStorage.getItem('activeTaskIds') || '[]');
      if (!savedIds.includes(taskId)) {
        savedIds.push(taskId);
        localStorage.setItem('activeTaskIds', JSON.stringify(savedIds));
      }
    }

    localStorage.setItem('pendingTalks', JSON.stringify(talks));
    setActiveTab("downloads");
    setAppState("idle");
  };

  const handleProcessingFinish = useCallback(() => {
    console.log("[App] handleProcessingFinish被调用，设置appState为preview");
    setAppState("preview");
  }, []);

  const handleStartLearning = async (talk: TedTalk) => {
    console.log("[App] handleStartLearning 被调用:", talk);

    try {
      if (currentTaskId) {
        await taskHistoryStorage.updateTaskStatus(
          currentTaskId,
          talk.id.toString(),
          "in_progress",
        );
      }
    } catch (error) {
      console.error("[App] 更新状态失败:", error);
    }

    setCurrentLearningTalk(talk);
    setAppState("learning");
    setActiveTab("chat");
  };

  const handleNavigateToLearning = async (talk: TedTalk) => {
    console.log("[App] handleNavigateToLearning 被调用:", talk.title);

    let chunks: any[] = [];
    let taskId = '';
    let tedTitle = talk.title;
    let tedSpeaker = talk.speaker;

    try {
      const history = await getHistoryList(50, 0);
      const taskHistory = history.find((h) =>
        h.ted_url === talk.url ||
        h.ted_title === talk.title ||
        (talk.title && h.ted_title && talk.title.includes(h.ted_title)) ||
        (h.ted_title && talk.title && h.ted_title.includes(talk.title.split('|')[0].trim()))
      );

      if (taskHistory) {
        const resultData = taskHistory.result;
        if (Array.isArray(resultData?.chunks)) {
          chunks = resultData.chunks.map((chunk: any) => {
            if (typeof chunk === 'string') {
              try {
                return dJSON.parse(chunk);
              } catch {
                return chunk;
              }
            }
            return chunk;
          });
        }
        taskId = taskHistory.task_id;
        tedTitle = taskHistory.ted_title || tedTitle;
        tedSpeaker = taskHistory.ted_speaker || tedSpeaker;
      }
    } catch (error) {
      console.error("[App] 获取历史记录失败:", error);
    }

    console.log("[App] 最终 chunks:", chunks.length, "taskId:", taskId);

    setCurrentTaskId(taskId);
    setReceivedChunks(chunks);
    setTedTitle(tedTitle);
    setTedSpeaker(tedSpeaker);
    setCurrentLearningTalk(talk);
    setActiveTab("chat");
    setAppState("learning_cards");
  };

  const handleComplete = useCallback(() => {
    console.log("[App] handleComplete 被调用");
    setHistoryInitialTab("completed");
    setActiveTab("history");
    setAppState("idle");
  }, []);

  const handleStartDebate = useCallback((title: string, speaker: string) => {
    console.log("[App] handleStartDebate 被调用:", title);
    setTedTitle(title);
    setTedSpeaker(speaker);
    setActiveTab("chat");
    setAppState("debate_select");
  }, []);

  const handleStartDebateFromSelect = useCallback((sessionId: string, opponentId: string, userRole: 'pro' | 'con', opponentName: string, openingMessage: string, systemPrompt: string, extractedArguments: string = "") => {
    console.log("[App] handleStartDebateFromSelect 被调用");
    setAppState("debate");
  }, []);

  const handleFirstChunkCompleted = useCallback(
    (taskId: string, receivedChunks: any[]) => {
      if (hasJumpedToLearningCards.current) {
        return;
      }

      console.log("[App] handleFirstChunkCompleted 被调用", taskId);
      hasJumpedToLearningCards.current = true;

      const parsedChunks = receivedChunks.map((chunk: any) => {
        if (typeof chunk === 'string') {
          try {
            return dJSON.parse(chunk);
          } catch {
            return chunk;
          }
        }
        return chunk;
      });

      setCurrentTaskId(taskId);
      setLastEventId(sseService.getLastEventId());
      setReceivedChunks(parsedChunks);
      setAppState("learning_cards");
    },
    [],
  );

  if (authStatus === "logged_out") {
    return <LoginPage onLogin={login} />;
  }

  return (
    <LearningContext.Provider value={learningContextValue}>
      <div className="flex h-screen font-sans overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white">
        <Navigation
          activeTab={activeTab}
          setActiveTab={(tab) => {
            setActiveTab(tab);
            setAppState("idle");
          }}
          userMode={authStatus}
          onLogout={logout}
        />
        <main className="flex-1 overflow-y-auto scroll-smooth w-full relative">
          {activeTab === "chat" &&
            (appState === "idle" ? (
              <SearchPage onStartProcessing={handleStartProcessing} />
            ) : appState === "processing" ? (
              <ProcessingPage
                taskId={currentTaskId}
                onFinish={handleProcessingFinish}
                onFirstChunkCompleted={handleFirstChunkCompleted}
              />
            ) : appState === "preview" ? (
              <PreviewPage
                selectedTalksData={processedTalks}
                onStartLearning={handleStartLearning}
                taskId={currentTaskId}
              />
          ) : appState === "learning_cards" ? (
             <LearningSessionPage
               onBack={() => {
                 setActiveTab("history")
                 setAppState("idle")
               }}
             />
            ) : appState === "debate_select" ? (
              <DebateSelectPage
                articleArgument={tedTitle}
                articleContent=""
                onBack={() => {
                  setActiveTab("history");
                  setAppState("idle");
                }}
                onStartDebate={handleStartDebateFromSelect}
              />
            ) : appState === "debate" ? (
              <DebatePage />
            ) : null)}
          {activeTab === "history" && (
            <HistoryPage
              initialTab={historyInitialTab}
              onStartDebate={(item) => handleStartDebate(item.ted_title, item.ted_speaker)}
            />
          )}
          {activeTab === "stats" && <StatsPage />}
          {activeTab === "downloads" && <DownloadsPage />}
          {activeTab === "vocab" && (
            <VocabPage
              vocabList={vocabList}
              onDeleteWord={deleteWord}
              onRefresh={refreshVocab}
            />
          )}
          {activeTab === "settings" && (
            <SettingsPage
              isDarkMode={isDarkMode}
              toggleTheme={() => setIsDarkMode(!isDarkMode)}
            />
          )}
        </main>
      </div>
    </LearningContext.Provider>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TaskProvider>
          <AuthWrapper />
          <Toaster position="top-right" />
        </TaskProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
