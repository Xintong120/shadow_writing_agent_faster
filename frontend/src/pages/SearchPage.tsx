// frontend/src/pages/SearchPage.tsx
// 搜索主页 - 包含标题、搜索输入和演讲选择功能
// 已集成 React Query

import { useState } from 'react'
import { Library, Zap, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import SearchInput from '@/components/SearchInput'
import TedCard from '@/components/TedCard'
import SkeletonCard from '@/components/SkeletonCard'
import { TedTalk } from '@/types/ted'
import { TaskHistoryItem } from '@/types/history'
import { api } from '@/services/api'
import { taskHistoryStorage } from '@/services/taskHistoryStorage'
import { handleError } from '@/utils/errorHandler'
import { useAuth } from '@/contexts/AuthContext'
import { useSearch } from '@/hooks/useSearch'

interface SearchPageProps {
  onStartProcessing?: (talks: TedTalk[], taskId?: string) => void
}

const SearchPage = ({ onStartProcessing }: SearchPageProps = {}) => {
  const { authStatus } = useAuth()
  const userId = authStatus === 'guest' ? 'guest_user' : 'user_123'

  const [query, setQuery] = useState('')
  const [selectedTalks, setSelectedTalks] = useState<string[]>([])

  const { data: searchResults, isLoading, isError, error, refetch } = useSearch(query, userId)

  const handleSearch = (newQuery: string) => {
    setQuery(newQuery)
  }

  const toggleTalk = (url: string) => {
    if (selectedTalks.includes(url)) {
      setSelectedTalks(selectedTalks.filter(selectedUrl => selectedUrl !== url))
    } else {
      setSelectedTalks([...selectedTalks, url])
    }
  }

  const candidatesToTedTalks = (candidates: typeof searchResults): (TedTalk & { url: string })[] => {
    return (candidates || []).map((candidate, index) => ({
      id: index + 1,
      title: candidate.title,
      speaker: candidate.speaker,
      duration: candidate.duration,
      views: candidate.views,
      description: candidate.description,
      thumbnail: `bg-blue-${100 + (index * 100) % 500} dark:bg-blue-900/30`,
      url: candidate.url
    }))
  }

  const startBatch = async () => {
    if (selectedTalks.length === 0) {
      toast.error('请至少选择一个TED演讲')
      return
    }

    try {
      const response = await api.startBatchProcess(selectedTalks, userId)
      toast.success('开始批量处理...')

      const selectedTedTalks = candidatesToTedTalks(searchResults).filter(talk =>
        selectedTalks.includes(talk.url)
      )

      const now = new Date().toISOString()
      const taskIds = response.task_ids || [response.task_id]  // 兼容旧版

      // 每个 TED 对应一个 task_id
      for (let i = 0; i < selectedTedTalks.length; i++) {
        const talk = selectedTedTalks[i]
        const talkId = talk.url
        const taskId = taskIds[i] || taskIds[0]  // 备用

        const existingTask = await taskHistoryStorage.getTaskByTalk(userId, talkId)

        if (existingTask) {
          existingTask.updatedAt = now
          existingTask.taskId = taskId  // 更新为新的 task_id
          await taskHistoryStorage.saveTask(existingTask)
        } else {
          const historyItem: TaskHistoryItem = {
            id: `${taskId}_${talkId}`,
            taskId: taskId,
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
        }
      }

      // 保存所有 task_id 到 localStorage
      localStorage.setItem('activeTaskIds', JSON.stringify(taskIds))

      onStartProcessing?.(selectedTedTalks, taskIds[0])
    } catch (error) {
      handleError(error, 'SearchPage.startBatch')
      toast.error('启动批量处理失败，请重试')
    }
  }

  const showResults = query.trim().length > 0 && (isLoading || isError || searchResults?.length > 0)
  const hasResults = searchResults && searchResults.length > 0

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 pb-24 md:pb-8">
      <div className={`transition-all duration-500 ${!showResults ? 'mt-20' : 'mt-0'}`}>
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 dark:text-white mb-4 tracking-tight">
            Shadow Writing <span className="text-indigo-600 dark:text-indigo-400">Mastery</span>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 max-w-2xl mx-auto">
            AI 驱动的 TED 演讲深度模仿学习系统
          </p>
        </div>
        <SearchInput onSearch={handleSearch} isSearching={isLoading} />
      </div>

      {showResults && (
        <div className="mt-12 animate-in fade-in slide-in-from-bottom-8">
          {hasResults && (
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
          )}

          {isError && (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 mb-4">
                <AlertCircle className="text-red-500" size={32} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">搜索失败</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                {(error as Error)?.message || '发生未知错误'}
              </p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
              >
                重试
              </button>
            </div>
          )}

          {isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6">
              {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
            </div>
          )}

          {hasResults && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6">
              {candidatesToTedTalks(searchResults).map(talk => (
                <TedCard
                  key={talk.url}
                  talk={talk}
                  isSelected={selectedTalks.includes(talk.url)}
                  onToggle={() => toggleTalk(talk.url)}
                />
              ))}
            </div>
          )}

          {hasResults && searchResults.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-500 dark:text-slate-400">
                没有找到关于「{query}」的TED演讲，请尝试其他关键词
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SearchPage
