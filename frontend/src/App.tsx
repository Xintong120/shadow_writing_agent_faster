import { useState, useEffect, useCallback } from "react";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { TaskProvider } from "@/contexts/TaskContext";
import { Toaster } from "sonner";

// 移除Lazy loading，直接导入组件
import LoginPage from "@/pages/LoginPage";
import SearchPage from "@/pages/SearchPage";
import ProcessingPage from "@/pages/ProcessingPage";
import PreviewPage from "@/pages/PreviewPage";
import LearningSessionPage from "@/pages/LearningSessionPage";
import LearningPage from "@/pages/LearningPage";
import HistoryPage from "@/pages/HistoryPage";
import SettingsPage from "@/pages/SettingsPage";
import StatsPage from "@/pages/StatsPage";
import Navigation from "@/components/Navigation";
import { ActiveTab } from "@/types/navigation";
import { TedTalk } from "@/types/ted";
import { LearningStatus } from "@/types/history";
import { taskHistoryStorage } from "@/services/taskHistoryStorage";

// Auth Wrapper Component with State Machine
const AuthWrapper = () => {
  const { authStatus, login, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [appState, setAppState] = useState<
    "idle" | "processing" | "preview" | "learning" | "learning_cards"
  >("idle");
  const [processedTalks, setProcessedTalks] = useState<TedTalk[]>([]);
  const [currentLearningTalk, setCurrentLearningTalk] =
    useState<TedTalk | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [historyInitialTab, setHistoryInitialTab] =
    useState<LearningStatus>("todo");

  // Apply dark mode to document element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDarkMode]);

  const handleStartProcessing = (talks: TedTalk[], taskId?: string) => {
    console.log("开始处理演讲:", talks, "taskId:", taskId);

    setProcessedTalks(talks);
    setCurrentTaskId(taskId || null);
    setAppState("processing");
  };

  const handleProcessingFinish = useCallback(() => {
    console.log("[App] handleProcessingFinish被调用，设置appState为preview");
    setAppState("preview");
    console.log("处理完成，跳转到预览页面");
  }, []);

  const handleStartLearning = async (talk: TedTalk) => {
    console.log(
      "[App] handleStartLearning 被调用:",
      talk,
      "taskId:",
      currentTaskId,
    );

    try {
      // 更新状态为 in_progress
      if (currentTaskId) {
        console.log(
          "[App] 尝试更新任务状态为 in_progress, taskId:",
          currentTaskId,
          "talkId:",
          talk.id,
        );
        await taskHistoryStorage.updateTaskStatus(
          currentTaskId,
          talk.id.toString(),
          "in_progress",
        );
        console.log("[App] 状态更新成功");
      } else {
        console.warn("[App] taskId为空，无法更新状态");
      }
    } catch (error) {
      console.error("[App] 更新状态失败:", error);
    }

    setCurrentLearningTalk(talk);
    setAppState("learning");
    setActiveTab("chat"); // 确保切换到 chat 标签显示学习页面
  };

  const handleNavigateToLearning = async (talk: TedTalk) => {
    console.log(
      "[App] handleNavigateToLearning 被调用:",
      talk,
      "taskId:",
      currentTaskId,
    );

    try {
      // 更新状态为 in_progress
      if (currentTaskId) {
        console.log(
          "[App] 尝试更新任务状态为 in_progress, taskId:",
          currentTaskId,
          "talkId:",
          talk.id,
        );
        await taskHistoryStorage.updateTaskStatus(
          currentTaskId,
          talk.id.toString(),
          "in_progress",
        );
        console.log("[App] 状态更新成功");
      } else {
        console.warn("[App] taskId为空，无法更新状态");
      }
    } catch (error) {
      console.error("[App] 更新状态失败:", error);
    }

    setActiveTab("chat");
    setCurrentLearningTalk(talk);
    setAppState("learning");
  };

  const handleComplete = () => {
    console.log("[App] handleComplete 被调用，导航到历史页面的completed标签页");
    setHistoryInitialTab("completed");
    setActiveTab("history");
    setAppState("idle");
  };

  // 新增：处理第一个chunk完成，跳转到学习卡片页面
  const handleFirstChunkCompleted = useCallback((taskId: string) => {
    console.log(
      "[App] handleFirstChunkCompleted 被调用，跳转到学习卡片页面",
      taskId,
    );
    setCurrentTaskId(taskId);
    setAppState("learning_cards");
  }, []);

  if (authStatus === "logged_out") {
    return <LoginPage onLogin={login} />;
  }

  // Main authenticated layout
  return (
    <div className="flex h-screen font-sans overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white">
      <Navigation
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setAppState("idle"); // 切换标签时重置状态
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
            <LearningPage
              taskId={currentTaskId}
              tedTitle={processedTalks[0]?.title}
              tedSpeaker={processedTalks[0]?.speaker}
            />
          ) : (
            currentTaskId && (
              <LearningSessionPage
                taskId={currentTaskId}
                onBack={() => setAppState("preview")}
                onComplete={handleComplete}
              />
            )
          ))}
        {activeTab === "history" && (
          <HistoryPage
            onNavigateToLearning={handleNavigateToLearning}
            initialTab={historyInitialTab}
          />
        )}
        {activeTab === "stats" && <StatsPage />}
        {activeTab === "settings" && (
          <SettingsPage
            isDarkMode={isDarkMode}
            toggleTheme={() => setIsDarkMode(!isDarkMode)}
          />
        )}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <TaskProvider>
        <AuthWrapper />
        <Toaster position="top-right" />
      </TaskProvider>
    </AuthProvider>
  );
}

export default App;
