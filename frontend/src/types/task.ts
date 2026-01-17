import { ShadowWritingResult } from './shadow'

// 任务相关类型定义
export type TaskStatus = 'idle' | 'searching' | 'running' | 'completed' | 'error'

export interface BatchTask {
  id: string
  urls: string[]
  status: TaskStatus
  progress: number        // 0-100
  currentUrl?: string
  results: ShadowWritingResult[]
  error?: string
  createdAt: number
  completedAt?: number    // 完成时间
  viewed?: boolean        // 是否已查看（用于通知栏）
  startedAt?: number      // 开始时间
}

