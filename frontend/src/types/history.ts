// frontend/src/types/history.ts
// 学习历史相关类型定义

import { TedTalk } from './ted'

// 学习记录状态
export type LearningStatus = 'todo' | 'in_progress' | 'completed'

// 学习历史记录（兼容现有UI）
export interface LearningHistory {
  id: number
  talkId: number
  title: string
  status: LearningStatus
  progress: number // 0-100
  lastPlayed: string // 如 "2h ago", "1d ago"
}

// 任务历史记录项（存储系统使用）
export interface TaskHistoryItem {
  id: string              // 唯一标识：`${taskId}_${talkId}`
  taskId: string          // 后端任务ID
  talkId: string          // TED演讲ID
  userId: string          // 用户ID（支持guest模式）
  tedTalk: TedTalk        // 演讲完整信息
  status: LearningStatus  // 'todo' | 'in_progress' | 'completed'
  progress: number        // 0-100
  createdAt: string       // 创建时间
  updatedAt: string       // 最后更新时间
  lastLearnedAt?: string  // 最后一次学习开始时间
  totalLearningTime: number // 累计学习时长（秒）
  learningSessions: number  // 学习次数
  unitCount?: number      // 练习单元数量
}

// 标签页配置
export interface HistoryTab {
  id: LearningStatus
  label: string
  icon: any // LucideIcon
  color: string // Tailwind 类名，如 'text-amber-500'
}