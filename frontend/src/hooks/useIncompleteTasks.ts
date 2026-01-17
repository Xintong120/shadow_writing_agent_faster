// frontend/src/hooks/useIncompleteTasks.ts
import { useLocalStorage } from './useLocalStorage'

export interface IncompleteTask {
  id: string
  title: string
  speaker: string
  total: number
  current: number
  lastViewedAt: number
}

/**
 * 获取未完成的学习任务
 * 从 localStorage 中读取最近查看的 Shadow Writing 结果
 * 只返回未完全看完的任务（current < total）
 */
export function useIncompleteTasks(): IncompleteTask[] {
  const [viewHistory] = useLocalStorage<Record<string, IncompleteTask>>('view_history', {})

  // 筛选未完成的任务，按最后查看时间排序
  const incompleteTasks = Object.values(viewHistory)
    .filter((task): task is IncompleteTask => task.current < task.total)
    .sort((a, b) => b.lastViewedAt - a.lastViewedAt)
    .slice(0, 3) // 最多显示3个未完成任务

  return incompleteTasks
}

/**
 * 更新任务查看进度
 */
export function useUpdateTaskProgress() {
  const [viewHistory, setViewHistory] = useLocalStorage<Record<string, IncompleteTask>>('view_history', {})

  const updateProgress = (taskId: string, data: Partial<IncompleteTask>) => {
    setViewHistory((prev: Record<string, IncompleteTask>) => ({
      ...prev,
      [taskId]: {
        ...prev[taskId],
        ...data,
        lastViewedAt: Date.now()
      } as IncompleteTask
    }))
  }

  return updateProgress
}