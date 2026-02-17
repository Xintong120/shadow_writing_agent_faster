// frontend/src/pages/HistoryPage.tsx
// 学习历史页面 - 展示学习记录，支持状态分组和跳转
// 已集成 React Query

import { useState, useEffect } from 'react'
import { Clock, Zap, CheckCircle, ArrowRight, Trash2, MessageSquare } from 'lucide-react'
import { LearningStatus, HistoryTab } from '@/types/history'
import { deleteHistoryRecord } from '@/services/downloadApi'
import { useAuth } from '@/contexts/AuthContext'
import { useLearning } from '@/contexts/LearningContext'
import { formatTimeAgo } from '@/utils/timeUtils'
import { useHistory } from '@/hooks/useHistory'
import SkeletonCard from '@/components/SkeletonCard'

const tabs: HistoryTab[] = [
  { id: 'todo', label: '待学习', icon: Clock, color: 'text-amber-500' },
  { id: 'in_progress', label: '学习中', icon: Zap, color: 'text-indigo-500' },
  { id: 'completed', label: '已完成', icon: CheckCircle, color: 'text-emerald-500' },
]

interface HistoryRecordItem {
  id: string
  task_id: string
  ted_title: string
  ted_speaker: string
  ted_url: string
  learned_at: string
  status: LearningStatus
}

interface HistoryPageProps {
  initialTab?: LearningStatus
  onStartDebate?: (item: HistoryRecordItem) => void
}

const HistoryPage = ({ initialTab = 'todo', onStartDebate }: HistoryPageProps) => {
  const { startLearningFromRecord } = useLearning()
  const [activeTab, setActiveTab] = useState<LearningStatus>(initialTab)

  const { data: historyItems, isLoading, isError, error, refetch } = useHistory()

  const handleDeleteHistory = async (item: HistoryRecordItem) => {
    if (confirm(`确定要删除"${item.ted_title}"的学习记录吗？此操作不可恢复。`)) {
      try {
        await deleteHistoryRecord(item.id)
        refetch()
      } catch (err) {
        console.error('删除历史记录失败:', err)
        alert('删除失败，请重试')
      }
    }
  }

  const handleStartLearning = (item: HistoryRecordItem) => {
    const record = {
      id: item.id,
      task_id: item.task_id,
      ted_title: item.ted_title,
      ted_speaker: item.ted_speaker,
      ted_url: item.ted_url,
      learned_at: item.learned_at,
    }
    startLearningFromRecord(record)
  }

  const handleActionClick = (item: HistoryRecordItem) => {
    if (activeTab === 'completed' && onStartDebate) {
      onStartDebate(item)
    } else {
      handleStartLearning(item)
    }
  }

  useEffect(() => {
    setActiveTab(initialTab)
  }, [initialTab])

  const filteredItems = historyItems?.filter(item => item.status === activeTab) || []

  const todoCount = historyItems?.filter(h => h.status === 'todo').length || 0
  const inProgressCount = historyItems?.filter(h => h.status === 'in_progress').length || 0
  const completedCount = historyItems?.filter(h => h.status === 'completed').length || 0

  const counts = { todo: todoCount, in_progress: inProgressCount, completed: completedCount }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 animate-in fade-in slide-in-from-bottom-4 pb-24 md:pb-8">
      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-8">学习历史</h1>

      <div className="flex gap-2 mb-8 bg-slate-100 dark:bg-slate-800/50 p-1.5 rounded-xl w-full sm:w-auto inline-flex">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 sm:flex-none px-6 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2 ${
              activeTab === tab.id
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            <tab.icon size={16} className={activeTab === tab.id ? tab.color : ''} />
            {tab.label}
            <span className="ml-1 text-xs opacity-60 bg-slate-100 dark:bg-slate-800 px-1.5 rounded-full">
              {counts[tab.id as keyof typeof counts]}
            </span>
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {isError && (
        <div className="text-center py-20 bg-red-50 dark:bg-red-900/20 rounded-2xl">
          <p className="text-red-600 dark:text-red-400 mb-4">{(error as Error)?.message || '加载失败'}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg"
          >
            重试
          </button>
        </div>
      )}

      {!isLoading && !isError && filteredItems.length === 0 && (
        <div className="text-center py-20 text-slate-500 dark:text-slate-400">
          <p>暂无学习记录</p>
        </div>
      )}

      {!isLoading && !isError && filteredItems.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-bold text-slate-900 dark:text-white mb-2">
                    {item.ted_title}
                  </h3>
                  <p className="text-sm text-indigo-600 dark:text-indigo-400 font-medium mb-2">
                    {item.ted_speaker}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {formatTimeAgo(item.learned_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleDeleteHistory(item)}
                    className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                    title="删除"
                  >
                    <Trash2 size={18} />
                  </button>
                  <button
                    onClick={() => handleActionClick(item)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                  >
                    {activeTab === 'completed' ? (
                      <>
                        <MessageSquare size={16} />
                        辩论练习
                      </>
                    ) : (
                      <>
                        开始学习
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HistoryPage
