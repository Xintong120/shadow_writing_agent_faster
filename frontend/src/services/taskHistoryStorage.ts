// frontend/src/services/taskHistoryStorage.ts
// 任务历史存储服务 - 支持localStorage和Electron本地文件存储

import { TaskHistoryItem, LearningStatus } from '@/types/history'
import { TedTalk } from '@/types/ted'

// 存储接口定义
export interface TaskHistoryStorage {
  saveTask(task: TaskHistoryItem): Promise<void>
  getTasks(userId: string): Promise<TaskHistoryItem[]>
  getTaskByTalk(userId: string, talkId: string): Promise<TaskHistoryItem | null>
  taskExists(userId: string, taskId: string, talkId: string): Promise<boolean>
  updateTaskStatus(taskId: string, talkId: string, status: LearningStatus): Promise<void>
  updateTaskProgress(taskId: string, talkId: string, progress: number): Promise<void>
  updateLastLearnedAt(taskId: string, talkId: string, lastLearnedAt: string): Promise<void>
  addLearningTime(taskId: string, talkId: string, durationSeconds: number): Promise<void>
  deleteTask(taskId: string, talkId: string): Promise<void>
  clearAll(userId: string): Promise<void>
}

// 检测是否为Electron环境
const isElectron = typeof window !== 'undefined' && (window as any).electronAPI

// localStorage实现
export class LocalStorageTaskHistoryStorage implements TaskHistoryStorage {
  private getStorageKey(userId: string): string {
    return `task_history_${userId}`
  }

  async saveTask(task: TaskHistoryItem): Promise<void> {
    try {
      const tasks = await this.getTasks(task.userId)
      const existingIndex = tasks.findIndex(t => t.id === task.id)

      if (existingIndex >= 0) {
        tasks[existingIndex] = { ...task }
      } else {
        tasks.push(task)
      }

      localStorage.setItem(this.getStorageKey(task.userId), JSON.stringify(tasks))
    } catch (error) {
      console.error('保存任务历史失败:', error)
      throw error
    }
  }

  async getTasks(userId: string): Promise<TaskHistoryItem[]> {
    try {
      const data = localStorage.getItem(this.getStorageKey(userId))
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('获取任务历史失败:', error)
      return []
    }
  }

  async getTaskByTalk(userId: string, talkId: string): Promise<TaskHistoryItem | null> {
    try {
      const tasks = await this.getTasks(userId)
      return tasks.find(task => task.talkId === talkId) || null
    } catch (error) {
      console.error('获取任务失败:', error)
      return null
    }
  }

  async taskExists(userId: string, taskId: string, talkId: string): Promise<boolean> {
    const task = await this.getTaskByTalk(userId, talkId)
    return task !== null
  }

  async updateTaskStatus(taskId: string, talkId: string, status: LearningStatus): Promise<void> {
    const taskIdWithTalkId = `${taskId}_${talkId}`

    // 遍历所有可能的用户ID
    for (const userId of ['user_123', 'guest_user']) {
      const tasks = await this.getTasks(userId)
      const task = tasks.find(t => t.id === taskIdWithTalkId)
      if (task) {
        task.status = status
        task.updatedAt = new Date().toISOString()
        await this.saveTask(task)
        break
      }
    }
  }

  async updateTaskProgress(taskId: string, talkId: string, progress: number): Promise<void> {
    const taskIdWithTalkId = `${taskId}_${talkId}`
    for (const userId of ['user_123', 'guest_user']) {
      const tasks = await this.getTasks(userId)
      const task = tasks.find(t => t.id === taskIdWithTalkId)
      if (task) {
        task.progress = progress
        task.updatedAt = new Date().toISOString()
        await this.saveTask(task)
        break
      }
    }
  }

  async updateLastLearnedAt(taskId: string, talkId: string, lastLearnedAt: string): Promise<void> {
    const taskIdWithTalkId = `${taskId}_${talkId}`
    for (const userId of ['user_123', 'guest_user']) {
      const tasks = await this.getTasks(userId)
      const task = tasks.find(t => t.id === taskIdWithTalkId)
      if (task) {
        task.lastLearnedAt = lastLearnedAt
        task.updatedAt = new Date().toISOString()
        await this.saveTask(task)
        break
      }
    }
  }

  async addLearningTime(taskId: string, talkId: string, durationSeconds: number): Promise<void> {
    const taskIdWithTalkId = `${taskId}_${talkId}`
    for (const userId of ['user_123', 'guest_user']) {
      const tasks = await this.getTasks(userId)
      const task = tasks.find(t => t.id === taskIdWithTalkId)
      if (task) {
        task.totalLearningTime += durationSeconds
        task.learningSessions += 1
        task.updatedAt = new Date().toISOString()
        await this.saveTask(task)
        break
      }
    }
  }

  async deleteTask(taskId: string, talkId: string): Promise<void> {
    const taskIdWithTalkId = `${taskId}_${talkId}`
    for (const userId of ['user_123', 'guest_user']) {
      const tasks = await this.getTasks(userId)
      const filteredTasks = tasks.filter(t => t.id !== taskIdWithTalkId)
      if (filteredTasks.length !== tasks.length) {
        localStorage.setItem(this.getStorageKey(userId), JSON.stringify(filteredTasks))
        break
      }
    }
  }

  async clearAll(userId: string): Promise<void> {
    localStorage.removeItem(this.getStorageKey(userId))
  }
}

// Electron文件存储实现
export class ElectronTaskHistoryStorage implements TaskHistoryStorage {
  private getFileName(userId: string): string {
    return `task_history_${userId}.json`
  }

  private async readTasksFromFile(userId: string): Promise<TaskHistoryItem[]> {
    try {
      if (!window.electronAPI?.readFile) {
        throw new Error('Electron API not available')
      }

      const data = await window.electronAPI.readFile(this.getFileName(userId))
      return data || []
    } catch (error) {
      console.warn('Failed to read tasks from file, returning empty array:', error)
      return []
    }
  }

  private async writeTasksToFile(userId: string, tasks: TaskHistoryItem[]): Promise<void> {
    try {
      if (!window.electronAPI?.writeFile) {
        throw new Error('Electron API not available')
      }

      await window.electronAPI.writeFile(this.getFileName(userId), tasks)
    } catch (error) {
      console.error('Failed to write tasks to file:', error)
      throw error
    }
  }

  async saveTask(task: TaskHistoryItem): Promise<void> {
    try {
      const tasks = await this.readTasksFromFile(task.userId)
      const existingIndex = tasks.findIndex(t => t.id === task.id)

      if (existingIndex >= 0) {
        tasks[existingIndex] = { ...task }
      } else {
        tasks.push(task)
      }

      await this.writeTasksToFile(task.userId, tasks)
    } catch (error) {
      console.error('Failed to save task:', error)
      // 回退到localStorage
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.saveTask(task)
    }
  }

  async getTasks(userId: string): Promise<TaskHistoryItem[]> {
    try {
      return await this.readTasksFromFile(userId)
    } catch (error) {
      console.warn('Failed to get tasks from file, trying localStorage:', error)
      // 回退到localStorage
      const fallback = new LocalStorageTaskHistoryStorage()
      return await fallback.getTasks(userId)
    }
  }

  async getTaskByTalk(userId: string, talkId: string): Promise<TaskHistoryItem | null> {
    try {
      const tasks = await this.readTasksFromFile(userId)
      return tasks.find(task => task.talkId === talkId) || null
    } catch (error) {
      console.warn('Failed to get task by talk from file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      return await fallback.getTaskByTalk(userId, talkId)
    }
  }

  async taskExists(userId: string, taskId: string, talkId: string): Promise<boolean> {
    try {
      const task = await this.getTaskByTalk(userId, talkId)
      return task !== null
    } catch (error) {
      console.warn('Failed to check task existence in file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      return await fallback.taskExists(userId, taskId, talkId)
    }
  }

  async updateTaskStatus(taskId: string, talkId: string, status: LearningStatus): Promise<void> {
    try {
      // 由于我们使用talkId作为唯一标识，我们需要遍历所有用户
      // 这里简化处理，假设当前操作的用户ID已知
      const userIds = ['user_123', 'guest_user']

      for (const userId of userIds) {
        const tasks = await this.readTasksFromFile(userId)
        const task = tasks.find(t => t.talkId === talkId)
        if (task) {
          task.status = status
          task.updatedAt = new Date().toISOString()
          await this.writeTasksToFile(userId, tasks)
          break
        }
      }
    } catch (error) {
      console.warn('Failed to update task status in file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.updateTaskStatus(taskId, talkId, status)
    }
  }

  async updateTaskProgress(taskId: string, talkId: string, progress: number): Promise<void> {
    try {
      const userIds = ['user_123', 'guest_user']

      for (const userId of userIds) {
        const tasks = await this.readTasksFromFile(userId)
        const task = tasks.find(t => t.talkId === talkId)
        if (task) {
          task.progress = progress
          task.updatedAt = new Date().toISOString()
          await this.writeTasksToFile(userId, tasks)
          break
        }
      }
    } catch (error) {
      console.warn('Failed to update task progress in file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.updateTaskProgress(taskId, talkId, progress)
    }
  }

  async updateLastLearnedAt(taskId: string, talkId: string, lastLearnedAt: string): Promise<void> {
    try {
      const userIds = ['user_123', 'guest_user']

      for (const userId of userIds) {
        const tasks = await this.readTasksFromFile(userId)
        const task = tasks.find(t => t.talkId === talkId)
        if (task) {
          task.lastLearnedAt = lastLearnedAt
          task.updatedAt = new Date().toISOString()
          await this.writeTasksToFile(userId, tasks)
          break
        }
      }
    } catch (error) {
      console.warn('Failed to update last learned at in file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.updateLastLearnedAt(taskId, talkId, lastLearnedAt)
    }
  }

  async addLearningTime(taskId: string, talkId: string, durationSeconds: number): Promise<void> {
    try {
      const userIds = ['user_123', 'guest_user']

      for (const userId of userIds) {
        const tasks = await this.readTasksFromFile(userId)
        const task = tasks.find(t => t.talkId === talkId)
        if (task) {
          task.totalLearningTime += durationSeconds
          task.learningSessions += 1
          task.updatedAt = new Date().toISOString()
          await this.writeTasksToFile(userId, tasks)
          break
        }
      }
    } catch (error) {
      console.warn('Failed to add learning time in file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.addLearningTime(taskId, talkId, durationSeconds)
    }
  }

  async deleteTask(taskId: string, talkId: string): Promise<void> {
    try {
      const userIds = ['user_123', 'guest_user']

      for (const userId of userIds) {
        const tasks = await this.readTasksFromFile(userId)
        const filteredTasks = tasks.filter(t => t.talkId !== talkId)
        if (filteredTasks.length !== tasks.length) {
          await this.writeTasksToFile(userId, filteredTasks)
          break
        }
      }
    } catch (error) {
      console.warn('Failed to delete task from file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.deleteTask(taskId, talkId)
    }
  }

  async clearAll(userId: string): Promise<void> {
    try {
      await window.electronAPI?.deleteFile(this.getFileName(userId))
    } catch (error) {
      console.warn('Failed to clear tasks from file, trying localStorage:', error)
      const fallback = new LocalStorageTaskHistoryStorage()
      await fallback.clearAll(userId)
    }
  }
}

// 全局存储实例
export const taskHistoryStorage: TaskHistoryStorage = isElectron
  ? new ElectronTaskHistoryStorage()
  : new LocalStorageTaskHistoryStorage()
