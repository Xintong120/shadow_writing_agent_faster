// frontend/src/contexts/TaskContext.tsx
// 全局任务管理
import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { toast } from 'sonner'

// 任务状态类型
export interface SearchTask {
  id: string
  query: string
  status: 'idle' | 'searching' | 'completed' | 'error'
  results?: any[]
  error?: string
}

export interface BatchTask {
  id: string
  urls: string[]
  status: 'idle' | 'running' | 'completed' | 'error'
  progress: number
  currentUrl?: string
  results?: any[]
  error?: string
  createdAt: number
  completedAt?: number
  viewed?: boolean
  startedAt?: number
}

export interface TaskContextType {
  tasks: {
    search: SearchTask | null
    batch: BatchTask[]
    current: any
    hasActive: boolean
  }
  startSearchTask: (query: string, searchFn: (query: string) => Promise<any[]>) => Promise<void>
  startBatchTask: (taskId: string, urls: string[]) => void
  updateTaskProgress: (taskId: string, data: Partial<BatchTask>) => void
  completeTask: (taskId: string) => void
}

const TaskContext = createContext<TaskContextType | undefined>(undefined)

interface TaskProviderProps {
  children: ReactNode
}

export function TaskProvider({ children }: TaskProviderProps) {
  const [tasks, setTasks] = useState<{
    search: SearchTask | null
    batch: BatchTask[]
    current: any
  }>({
    search: null,
    batch: [],
    current: null,
  })

  // 开始搜索任务
  const startSearchTask = useCallback(async (
    query: string,
    searchFn: (query: string) => Promise<any[]>
  ) => {
    const taskId = `search_${Date.now()}`

    setTasks(prev => ({
      ...prev,
      search: {
        id: taskId,
        query,
        status: 'searching',
        results: []
      }
    }))

    try {
      const results = await searchFn(query)

      setTasks(prev => ({
        ...prev,
        search: prev.search ? {
          ...prev.search,
          status: 'completed',
          results
        } : null
      }))

      toast.success(`找到了 ${results.length} 个演讲！`)
    } catch (error) {
      setTasks(prev => ({
        ...prev,
        search: prev.search ? {
          ...prev.search,
          status: 'error',
          error: error instanceof Error ? error.message : '未知错误'
        } : null
      }))
      toast.error('搜索失败')
    }
  }, [])

  // 开始批量处理任务
  const startBatchTask = useCallback((taskId: string, urls: string[]) => {
    const newTask: BatchTask = {
      id: taskId,
      urls,
      status: 'running',
      progress: 0,
      createdAt: Date.now(),
      startedAt: Date.now()
    }

    setTasks(prev => ({
      ...prev,
      batch: [...prev.batch, newTask]
    }))
  }, [])

  // 更新任务进度
  const updateTaskProgress = useCallback((taskId: string, data: Partial<BatchTask>) => {
    setTasks(prev => ({
      ...prev,
      batch: prev.batch.map(task =>
        task.id === taskId
          ? { ...task, ...data }
          : task
      )
    }))
  }, [])

  // 完成任务
  const completeTask = useCallback((taskId: string) => {
    setTasks(prev => ({
      ...prev,
      batch: prev.batch.map(task =>
        task.id === taskId
          ? { ...task, status: 'completed', completedAt: Date.now() }
          : task
      )
    }))

    toast.success('处理完成！', {
      action: {
        label: '查看结果',
        onClick: () => {
          window.location.pathname = `/results/${taskId}`
        }
      }
    })
  }, [])

  // 检查是否有活跃任务
  const hasActive = tasks.search?.status === 'searching' ||
                   tasks.batch.some(t => t.status === 'running')

  return (
    <TaskContext.Provider value={{
      tasks: { ...tasks, hasActive },
      startSearchTask,
      startBatchTask,
      updateTaskProgress,
      completeTask
    }}>
      {children}
    </TaskContext.Provider>
  )
}

export const useTasks = (): TaskContextType => {
  const context = useContext(TaskContext)
  if (!context) {
    throw new Error('useTasks must be used within TaskProvider')
  }
  return context
}