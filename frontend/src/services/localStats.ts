// frontend/src/services/localStats.ts
// 本地统计数据服务 - 从 taskHistoryStorage 计算统计信息

import { taskHistoryStorage } from './taskHistoryStorage'
import { TaskHistoryItem } from '@/types/history'

// 核心统计数据接口
export interface LocalStats {
  totalLearningTime: number // 总练习时长（秒）
  totalSentences: number // 累计模仿句子数
  totalTedTalks: number // 完成TED演讲数
}

// 热力图数据接口
export interface HeatmapData {
  day: number // 日期 (1-31)
  count: number // 当天学习活动数量
  date: string // ISO日期字符串
}

// 学习目标接口
export interface LearningGoals {
  daily: { target: number; current: number; unit: string }
  weekly: { target: number; current: number; unit: string }
  monthly: { target: number; current: number; unit: string }
}

// 默认学习目标
const DEFAULT_GOALS: LearningGoals = {
  daily: { target: 20, current: 12, unit: '句' },
  weekly: { target: 140, current: 85, unit: '句' },
  monthly: { target: 600, current: 342, unit: '句' }
}

/**
 * 获取用户统计数据
 */
export const getLocalStats = async (userId: string): Promise<LocalStats> => {
  try {
    const tasks = await taskHistoryStorage.getTasks(userId)

    // 计算总练习时长
    const totalLearningTime = tasks.reduce((sum, task) => sum + (task.totalLearningTime || 0), 0)

    // 计算模仿句子总数（使用 unitCount 或者用 learningSessions 估算）
    const totalSentences = tasks.reduce((sum, task) => {
      return sum + (task.unitCount || task.learningSessions * 5) // 假设每个学习会话5个句子
    }, 0)

    // 计算TED演讲数（去重talkId）
    const uniqueTedTalks = new Set(tasks.map(task => task.talkId))
    const totalTedTalks = uniqueTedTalks.size

    return {
      totalLearningTime,
      totalSentences,
      totalTedTalks
    }
  } catch (error) {
    console.error('获取本地统计数据失败:', error)
    return {
      totalLearningTime: 0,
      totalSentences: 0,
      totalTedTalks: 0
    }
  }
}

/**
 * 生成热力图数据
 * 从学习记录中按日期聚合活动数量
 */
export const generateHeatmapData = async (userId: string, year: number, month: number): Promise<HeatmapData[]> => {
  try {
    const tasks = await taskHistoryStorage.getTasks(userId)
    const daysInMonth = new Date(year, month + 1, 0).getDate()

    // 初始化每天的数据
    const dailyActivity: { [key: string]: number } = {}

    // 从任务中提取学习活动
    tasks.forEach(task => {
      if (task.lastLearnedAt) {
        const date = new Date(task.lastLearnedAt)
        if (date.getFullYear() === year && date.getMonth() === month) {
          const day = date.getDate()
          const dateKey = date.toISOString().split('T')[0]

          // 使用学习会话数作为活动计数
          dailyActivity[dateKey] = (dailyActivity[dateKey] || 0) + task.learningSessions
        }
      }
    })

    // 生成完整月份的数据
    const heatmapData: HeatmapData[] = []
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day)
      const dateKey = date.toISOString().split('T')[0]
      const count = dailyActivity[dateKey] || 0

      heatmapData.push({
        day,
        count,
        date: dateKey
      })
    }

    return heatmapData
  } catch (error) {
    console.error('生成热力图数据失败:', error)
    // 返回空数据
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    return Array.from({ length: daysInMonth }, (_, i) => ({
      day: i + 1,
      count: 0,
      date: new Date(year, month, i + 1).toISOString().split('T')[0]
    }))
  }
}

/**
 * 获取用户学习目标
 */
export const getLearningGoals = (userId: string): LearningGoals => {
  try {
    const storageKey = `learning_goals_${userId}`
    const stored = localStorage.getItem(storageKey)
    return stored ? JSON.parse(stored) : DEFAULT_GOALS
  } catch (error) {
    console.error('获取学习目标失败:', error)
    return DEFAULT_GOALS
  }
}

/**
 * 保存用户学习目标
 */
export const saveLearningGoals = (userId: string, goals: LearningGoals): void => {
  try {
    const storageKey = `learning_goals_${userId}`
    localStorage.setItem(storageKey, JSON.stringify(goals))
  } catch (error) {
    console.error('保存学习目标失败:', error)
  }
}

/**
 * 更新特定周期的目标
 */
export const updateGoal = (userId: string, period: 'daily' | 'weekly' | 'monthly', target: number): void => {
  const goals = getLearningGoals(userId)
  goals[period].target = target
  saveLearningGoals(userId, goals)
}

/**
 * 获取当前目标进度（从任务数据计算）
 */
export const getCurrentGoalProgress = async (userId: string, period: 'daily' | 'weekly' | 'monthly'): Promise<number> => {
  try {
    const tasks = await taskHistoryStorage.getTasks(userId)
    const now = new Date()

    let startDate: Date
    let endDate: Date = new Date(now)

    switch (period) {
      case 'daily':
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        break
      case 'weekly':
        const dayOfWeek = now.getDay()
        startDate = new Date(now.getTime() - dayOfWeek * 24 * 60 * 60 * 1000)
        startDate.setHours(0, 0, 0, 0)
        break
      case 'monthly':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1)
        break
    }

    // 计算指定时间段内的句子数
    const periodTasks = tasks.filter(task => {
      if (!task.lastLearnedAt) return false
      const taskDate = new Date(task.lastLearnedAt)
      return taskDate >= startDate && taskDate <= endDate
    })

    const current = periodTasks.reduce((sum, task) => {
      return sum + (task.unitCount || task.learningSessions * 5)
    }, 0)

    return current
  } catch (error) {
    console.error('计算目标进度失败:', error)
    return 0
  }
}