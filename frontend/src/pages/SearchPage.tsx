// frontend/src/pages/SearchPage.tsx
// 搜索主页 - 包含标题、搜索输入和演讲选择功能
// 已集成后端API：使用 api.searchTED 进行TED搜索，api.startBatchProcess 启动批量处理

import { useState } from 'react'
import { Library, Zap } from 'lucide-react'
import { toast } from 'sonner' // 用于显示用户友好的错误提示
import SearchInput from '@/components/SearchInput'
import TedCard from '@/components/TedCard'
import { TedTalk, SearchStatus, TEDCandidate } from '@/types/ted' // 添加 TEDCandidate 类型
import { TaskHistoryItem } from '@/types/history' // 添加历史记录类型
import { api } from '@/services/api' // 导入API服务
import { taskHistoryStorage } from '@/services/taskHistoryStorage' // 导入历史存储服务
import { handleError } from '@/utils/errorHandler' // 错误处理工具
import { useAuth } from '@/contexts/AuthContext' // 用于获取用户认证状态

// 模拟数据
const MOCK_TED_TALKS: TedTalk[] = [
  {
    id: 1,
    title: "Why AI needs a sense of ethics",
    speaker: "Technologist X",
    duration: "12:45",
    views: "2.1M",
    description: "An insightful look into how we can program morality into machines...",
    thumbnail: "bg-blue-100 dark:bg-blue-900/30"
  },
  {
    id: 2,
    title: "The future of leadership in the digital age",
    speaker: "Leader Y",
    duration: "15:20",
    views: "1.5M",
    description: "What does it mean to lead when your team is half human, half algorithm?",
    thumbnail: "bg-indigo-100 dark:bg-indigo-900/30"
  },
  {
    id: 3,
    title: "How to learn a new language by 2025",
    speaker: "Linguist Z",
    duration: "09:30",
    views: "5.8M",
    description: "New techniques in cognitive science reveal the secrets of rapid acquisition.",
    thumbnail: "bg-purple-100 dark:bg-purple-900/30"
  },
  {
    id: 4,
    title: "Creative thinking in a data-driven world",
    speaker: "Artist A",
    duration: "18:10",
    views: "900K",
    description: "Why human creativity is becoming more valuable, not less.",
    thumbnail: "bg-pink-100 dark:bg-pink-900/30"
  }
]

interface SearchPageProps {
  onStartProcessing?: (talks: TedTalk[], taskId?: string) => void
}

const SearchPage = ({ onStartProcessing }: SearchPageProps = {}) => {
  // 使用认证 hooks
  const { authStatus } = useAuth()

  // 根据认证状态确定用户ID
  const userId = authStatus === 'guest' ? 'guest_user' : 'user_123'

  // 搜索相关状态
  const [searchStatus, setSearchStatus] = useState<SearchStatus>('idle')
  const [searchResults, setSearchResults] = useState<TEDCandidate[]>([]) // 后端返回的TED候选列表
  const [isSearching, setIsSearching] = useState(false) // 搜索加载状态
  const [error, setError] = useState<string | null>(null) // 错误信息

  // 选中的TED URLs（改为string数组，因为使用URL作为唯一标识）
  const [selectedTalks, setSelectedTalks] = useState<string[]>([])

  // 处理TED搜索 - 调用后端API
  const handleSearch = async (query: string) => {
    if (!query.trim()) return

    console.log(`[SearchPage] 开始搜索: "${query}", userId: ${userId}`)
    setIsSearching(true)
    setSearchStatus('searching')
    setError(null) // 清空之前的错误

    try {
      console.log('[SearchPage] 调用api.searchTED...')
      // 调用后端API搜索TED
      const response = await api.searchTED(query, userId)
      console.log('[SearchPage] API响应:', response)

      // 更新搜索结果
      setSearchResults(response.candidates)
      setSearchStatus('results')
      console.log(`[SearchPage] 设置搜索状态为'results', 结果数量: ${response.candidates.length}`)

      // 显示搜索结果提示
      if (response.candidates.length > 0) {
        toast.success(`找到 ${response.candidates.length} 个关于"${query}"的TED演讲`)
      } else {
        toast.info(`没有找到关于"${query}"的TED演讲，请尝试其他关键词`)
      }
    } catch (error) {
      console.error('[SearchPage] 搜索TED失败:', error)
      // 处理搜索错误
      setError('搜索过程中出现错误，请稍后重试')
      setSearchStatus('idle')
      handleError(error, 'SearchPage.handleSearch')
      toast.error('搜索失败，请检查网络连接')
    } finally {
      setIsSearching(false)
      console.log('[SearchPage] 搜索完成, isSearching设为false')
    }
  }

  // 切换TED选择状态（使用URL作为标识）
  const toggleTalk = (url: string) => {
    if (selectedTalks.includes(url)) {
      setSelectedTalks(selectedTalks.filter(selectedUrl => selectedUrl !== url))
    } else {
      setSelectedTalks([...selectedTalks, url])
    }
  }

  // 将TEDCandidate转换为扩展的TedTalk格式（用于前端显示）
  const candidatesToTedTalks = (candidates: TEDCandidate[]): (TedTalk & { url: string })[] => {
    return candidates.map((candidate, index) => ({
      id: index + 1, // 生成临时ID，后续可使用URL哈希
      title: candidate.title,
      speaker: candidate.speaker,
      duration: candidate.duration,
      views: candidate.views,
      description: candidate.description,
      thumbnail: `bg-blue-${100 + (index * 100) % 500} dark:bg-blue-900/30`, // 动态生成背景色
      url: candidate.url // 添加URL用于选择逻辑
    }))
  }

  // 开始批量处理 - 调用后端API启动批量任务
  const startBatch = async () => {
    if (selectedTalks.length === 0) {
      toast.error('请至少选择一个TED演讲')
      return
    }

    try {
      // 调用后端API启动批量处理
      const response = await api.startBatchProcess(selectedTalks, userId)

      // 显示成功消息
      toast.success('开始批量处理...')

      // 将选中的TED转换为TedTalk格式
      const selectedTedTalks = candidatesToTedTalks(searchResults).filter(talk =>
        selectedTalks.includes(talk.url)
      )

      // 为每个演讲创建历史记录（避免重复）
      const now = new Date().toISOString()
      for (const talk of selectedTedTalks) {
        const talkId = talk.url
        const existingTask = await taskHistoryStorage.getTaskByTalk(userId, talkId)

        if (existingTask) {
          // 如果已存在，更新基本信息但保持当前状态
          existingTask.updatedAt = now
          await taskHistoryStorage.saveTask(existingTask)
          console.log(`[SearchPage] 更新现有历史记录: ${existingTask.id}`)
        } else {
          // 创建新记录，初始状态为todo
          const historyItem: TaskHistoryItem = {
            id: `${response.task_id}_${talkId}`,
            taskId: response.task_id,
            talkId: talkId,
            userId: userId,
            tedTalk: talk,
            status: 'todo',
            progress: 0,
            createdAt: now,
            updatedAt: now,
            totalLearningTime: 0,
            learningSessions: 0
          }

          await taskHistoryStorage.saveTask(historyItem)
          console.log(`[SearchPage] 创建历史记录: ${historyItem.id}`)
        }
      }

      // 调用父组件的处理函数
      onStartProcessing?.(selectedTedTalks, response.task_id)

    } catch (error) {
      console.error('启动批量处理失败:', error)
      handleError(error, 'SearchPage.startBatch')
      toast.error('启动批量处理失败，请重试')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 pb-24 md:pb-8">
      <div className={`transition-all duration-500 ${searchStatus === 'idle' ? 'mt-20' : 'mt-0'}`}>
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4 tracking-tight">
            Shadow Writing <span className="text-indigo-600 dark:text-indigo-400">Mastery</span>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 max-w-2xl mx-auto">
            AI 驱动的 TED 演讲深度模仿学习系统
          </p>
        </div>
        <SearchInput onSearch={handleSearch} isSearching={searchStatus === 'searching'} />
      </div>

      {searchStatus === 'results' && (
        <div className="mt-12 animate-in fade-in slide-in-from-bottom-8">
          <div className="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <Library className="text-indigo-500" /> 推荐演讲
            </h2>
            {selectedTalks.length > 0 && (
              <button
                onClick={startBatch}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium shadow-md transition-all flex items-center gap-2 animate-in fade-in"
              >
                <Zap size={18} />
                开始处理 ({selectedTalks.length})
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {candidatesToTedTalks(searchResults).map(talk => (
              <TedCard
                key={talk.url} // 使用URL作为唯一key
                talk={talk}
                isSelected={selectedTalks.includes(talk.url)}
                onToggle={() => toggleTalk(talk.url)} // 传递URL给toggle函数
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SearchPage
