// frontend/src/pages/HistoryPage.tsx
// 学习历史页面 - 展示学习记录，支持状态分组和跳转

import { useState, useEffect } from 'react'
import { Clock, Zap, CheckCircle, ArrowRight, List, Trash2 } from 'lucide-react'
import { LearningStatus, LearningHistory, HistoryTab, TaskHistoryItem } from '@/types/history'
import { TedTalk } from '@/types/ted'
import { taskHistoryStorage } from '@/services/taskHistoryStorage'
import { useAuth } from '@/contexts/AuthContext'

// 标签页配置
const tabs: HistoryTab[] = [
  { id: 'todo', label: '待学习', icon: Clock, color: 'text-amber-500' },
  { id: 'in_progress', label: '学习中', icon: Zap, color: 'text-indigo-500' },
  { id: 'completed', label: '已完成', icon: CheckCircle, color: 'text-emerald-500' },
]

// 时间格式化工具函数
const formatTimeAgo = (dateString: string | undefined): string => {
  if (!dateString) return '未知时间'

  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

interface HistoryPageProps {
  onNavigateToLearning: (talk: TedTalk) => void
  initialTab?: LearningStatus
}

const HistoryPage = ({ onNavigateToLearning, initialTab = 'todo' }: HistoryPageProps) => {
  const { authStatus } = useAuth()
  const [activeTab, setActiveTab] = useState<LearningStatus>(initialTab)
  const [historyItems, setHistoryItems] = useState<TaskHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 删除历史记录
  const handleDeleteHistory = async (item: TaskHistoryItem) => {
    if (confirm(`确定要删除"${item.tedTalk.title}"的学习记录吗？此操作不可恢复。`)) {
      try {
        const userId = getUserId()
        await taskHistoryStorage.deleteTask(item.taskId, item.talkId)

        // 重新加载数据
        const updatedTasks = await taskHistoryStorage.getTasks(userId)
        setHistoryItems(updatedTasks)

        console.log(`[HistoryPage] 删除历史记录: ${item.id}`)
      } catch (err) {
        console.error('删除历史记录失败:', err)
        alert('删除失败，请重试')
      }
    }
  }

  // 获取用户ID
  const getUserId = () => authStatus === 'guest' ? 'guest_user' : 'user_123'

  // 加载历史数据
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setLoading(true)
        const userId = getUserId()
        const tasks = await taskHistoryStorage.getTasks(userId)
        setHistoryItems(tasks)
      } catch (err) {
        console.error('加载历史数据失败:', err)
        setError('加载历史数据失败')
      } finally {
        setLoading(false)
      }
    }

    loadHistory()
  }, [authStatus])

  // 当initialTab改变时更新activeTab
  useEffect(() => {
    setActiveTab(initialTab)
  }, [initialTab])

  // 根据活跃标签过滤数据
  const filteredHistory = historyItems.filter(item => item.status === activeTab)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 animate-in fade-in slide-in-from-bottom-4 pb-24 md:pb-8">
      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-8">学习历史</h1>

      {/* Tabs */}
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
              {historyItems.filter(h => h.status === tab.id).length}
            </span>
          </button>
        ))}
      </div>

      {/* List */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p>加载历史记录...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20 bg-red-50 dark:bg-red-900/20 rounded-2xl">
            <p className="text-red-600 dark:text-red-400">{error}</p>
          </div>
        ) : filteredHistory.length > 0 ? (
          filteredHistory.map((item) => {
            // 使用item.tedTalk数据构建完整的TedTalk对象
            const talk: TedTalk = {
              id: parseInt(item.talkId) || 1,
              title: item.tedTalk.title,
              speaker: item.tedTalk.speaker,
              duration: item.tedTalk.duration,
              views: item.tedTalk.views,
              description: item.tedTalk.description,
              thumbnail: item.tedTalk.thumbnail
            }

            return (
              <div
                key={item.id}
                onClick={() => onNavigateToLearning(talk)}
                className="group bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-500 transition-all cursor-pointer flex items-center gap-5"
              >
                {/* Thumbnail / Status Icon */}
                <div className={`w-16 h-16 rounded-xl flex items-center justify-center shrink-0 ${
                    activeTab === 'completed' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400' :
                    activeTab === 'in_progress' ? 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400' :
                    'bg-amber-100 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400'
                }`}>
                    {activeTab === 'completed' ? <CheckCircle size={28} /> :
                     activeTab === 'in_progress' ? <Zap size={28} /> :
                     <Clock size={28} />}
                </div>

                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-lg text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {item.tedTalk.title}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 mt-1">
                    <span>{item.tedTalk.speaker}</span>
                    <span>•</span>
                    <span>{formatTimeAgo(item.lastLearnedAt || item.updatedAt)}</span>
                  </div>

                  {/* Progress Bar (Only for In Progress) */}
                  {activeTab === 'in_progress' && (
                    <div className="mt-3 w-full max-w-xs h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                       <div className="h-full bg-indigo-500 rounded-full" style={{width: `${item.progress}%`}}></div>
                    </div>
                  )}
                </div>

                <div className="hidden sm:flex items-center gap-2">
                  {/* 删除按钮 */}
                  <div
                    onClick={(e) => {
                      e.stopPropagation() // 阻止事件冒泡
                      handleDeleteHistory(item)
                    }}
                    className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-700 text-slate-400 hover:bg-pink-100 hover:text-pink-600 dark:hover:bg-pink-900/20 dark:hover:text-pink-400 transition-all flex items-center justify-center cursor-pointer"
                  >
                    <Trash2 size={18} />
                  </div>

                  {/* 进入学习按钮 */}
                  <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-700 text-slate-400 group-hover:bg-indigo-600 group-hover:text-white transition-all flex items-center justify-center">
                    <ArrowRight size={20} />
                  </div>
                </div>
              </div>
            )
          })
        ) : (
          <div className="text-center py-20 bg-white dark:bg-slate-800 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
              <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
                 <List size={32} />
              </div>
              <p className="text-slate-500 dark:text-slate-400">暂无此状态的记录</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default HistoryPage