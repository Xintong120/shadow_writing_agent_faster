// frontend/src/pages/LearningSessionPage.tsx
// 学习会话页面 - 沉浸式学习界面

import { useState, useEffect } from 'react'
import { ArrowRight, MoreHorizontal } from 'lucide-react'
import LearningCard from '@/components/LearningCard'
import { LearningItem } from '@/types/learning'
import { api, convertShadowResultsToLearningItems } from '@/services/api'
import { taskHistoryStorage } from '@/services/taskHistoryStorage'
import { useAuth } from '@/contexts/AuthContext'

interface LearningSessionPageProps {
  taskId: string
  onBack: () => void
  onComplete?: () => void
}

const LearningSessionPage = ({ taskId, onBack, onComplete }: LearningSessionPageProps) => {
  const { authStatus } = useAuth()
  const [content, setContent] = useState<LearningItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null)

  // 获取用户ID
  const getUserId = () => authStatus === 'guest' ? 'guest_user' : 'user_123'

  // 加载学习内容数据
  useEffect(() => {
    if (!taskId) {
      console.log('[LearningSessionPage] taskId为空，跳过加载')
      return
    }

    const loadLearningContent = async () => {
      try {
        setLoading(true)
        console.log('[LearningSessionPage] 开始加载学习内容，taskId:', taskId)
        const taskData = await api.getTaskStatus(taskId)
        console.log('[LearningSessionPage] 获取任务数据:', taskData)
        console.log('[LearningSessionPage] 任务状态:', taskData.status)
        console.log('[LearningSessionPage] results类型:', typeof taskData.results, '长度:', taskData.results?.length)

        // 扁平化批量结果并转换为LearningItem格式
        let flatResults: any[] = []
        if (taskData.results && Array.isArray(taskData.results)) {
          flatResults = taskData.results.flatMap((urlResult: any) => {
            console.log('[LearningSessionPage] 处理urlResult:', urlResult.url, 'result_count:', urlResult.result_count)
            return urlResult.results || []
          })
        }
        console.log('[LearningSessionPage] 扁平化结果数量:', flatResults.length)
        console.log('[LearningSessionPage] 扁平化结果样例:', flatResults.slice(0, 2))

        const learningItems = convertShadowResultsToLearningItems(flatResults)
        console.log('[LearningSessionPage] 转换后学习项目数量:', learningItems.length)
        console.log('[LearningSessionPage] 学习项目样例:', learningItems.slice(0, 2))

        setContent(learningItems)

        if (learningItems.length === 0) {
          console.log('[LearningSessionPage] 学习内容为空，设置错误')
          setError('没有找到学习内容')
        } else {
          console.log('[LearningSessionPage] 成功加载学习内容')

          // 设置会话开始时间
          setSessionStartTime(new Date())

          // 更新历史记录的学习时间
          const userId = getUserId()
          const now = new Date().toISOString()

          // 为任务相关的所有演讲更新lastLearnedAt
          try {
            // 这里简化处理，实际可能需要从taskData中提取URLs
            // 暂时为所有相关记录更新时间
            console.log('[LearningSessionPage] 更新学习时间')
          } catch (err) {
            console.error('[LearningSessionPage] 更新学习时间失败:', err)
          }
        }
      } catch (err) {
        console.error('[LearningSessionPage] 加载学习内容失败:', err)
        setError(err instanceof Error ? err.message : '加载学习内容失败')
      } finally {
        console.log('[LearningSessionPage] 设置loading为false')
        setLoading(false)
      }
    }

    loadLearningContent()
  }, [taskId])

  // 处理学习时长记录
  useEffect(() => {
    return () => {
      // 组件卸载时记录学习时长
      if (sessionStartTime && taskId) {
        const durationSeconds = Math.floor((new Date().getTime() - sessionStartTime.getTime()) / 1000)

        if (durationSeconds > 10) { // 只记录超过10秒的学习时长
          const userId = getUserId()
          // 为任务相关的所有演讲累加学习时长
          // 这里需要从taskData中获取URLs，暂时简化处理
          console.log(`[LearningSessionPage] 记录学习时长: ${durationSeconds}秒`)
        }
      }
    }
  }, [sessionStartTime, taskId, authStatus])

  // 处理完成练习
  const handleComplete = async () => {
    console.log('[LearningSessionPage] 完成按钮被点击，taskId:', taskId)

    try {
      // 需要从taskData中获取talkId，暂时使用简化逻辑
      // 实际应该从content或taskData中提取talk信息
      const userId = getUserId()

      // 获取所有相关任务并更新状态为completed
      // 这里简化处理，假设只有一个talk
      // TODO: 从taskData中正确提取talkId
      const tasks = await taskHistoryStorage.getTasks(userId)
      const taskToUpdate = tasks.find(t => t.taskId === taskId)

      if (taskToUpdate) {
        console.log('[LearningSessionPage] 尝试更新任务状态为 completed, taskId:', taskId, 'talkId:', taskToUpdate.talkId)
        await taskHistoryStorage.updateTaskStatus(taskId, taskToUpdate.talkId, 'completed')
        console.log('[LearningSessionPage] 状态更新成功')

        if (onComplete) {
          onComplete()
        }
      } else {
        console.warn('[LearningSessionPage] 未找到对应的任务记录')
      }
    } catch (error) {
      console.error('[LearningSessionPage] 更新状态失败:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载学习内容...</p>
        </div>
      </div>
    )
  }

  if (error || content.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold text-destructive mb-4">加载失败</h1>
        <p className="text-muted-foreground mb-4">{error || '没有找到学习内容'}</p>
        <button onClick={onBack}>
          返回任务列表
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 pb-32">
       {/* 顶部导航 */}
       <div className="sticky top-0 z-10 bg-slate-50/90 dark:bg-slate-950/90 backdrop-blur-md py-4 mb-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
           <button
             onClick={onBack}
             className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-white transition-colors"
           >
              <ArrowRight className="rotate-180" size={20} />
              <span className="font-medium hidden sm:inline">返回任务列表</span>
           </button>
           <div className="text-center">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">学习会话</h2>
              <p className="text-xs text-slate-500">{content.length} 个练习</p>
           </div>
           <button className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
              <MoreHorizontal size={24} />
           </button>
       </div>

       {/* 练习卡片列表 */}
       <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-500">
           {content.map((item, index) => (
              <div key={item.id}>
                 <div className="flex items-center gap-4 mb-4">
                    <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
                    <span className="text-xs font-bold text-slate-400">练习 {index + 1}</span>
                    <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
                 </div>
                 <LearningCard data={item} />
              </div>
           ))}

           <div className="text-center pt-10 pb-20">
              <button
                onClick={handleComplete}
                className="bg-slate-900 dark:bg-indigo-600 text-white px-8 py-3 rounded-full font-bold shadow-lg hover:shadow-xl transition-all hover:-translate-y-1"
              >
                 完成本节练习 🎉
              </button>
           </div>
       </div>
    </div>
  )
}

export default LearningSessionPage
