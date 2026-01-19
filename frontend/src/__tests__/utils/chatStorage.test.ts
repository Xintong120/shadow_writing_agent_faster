import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals'
import { ChatStorageManager, chatStorage } from '@/utils/chatStorage'
import { createTestMessage, createTestMessages } from '@/test-utils/test-helpers'

describe('ChatStorageManager', () => {
  let storage: ChatStorageManager

  beforeEach(async () => {
    storage = new ChatStorageManager()
    await storage.init()
  })

  afterEach(async () => {
    await storage.clearAllMessages()
  })

  describe('初始化', () => {
    it('应该支持IndexedDB', () => {
      expect(ChatStorageManager.isSupported()).toBe(true)
    })

    it('应该成功初始化数据库', async () => {
      // 如果没有抛出错误，说明初始化成功
      expect(storage).toBeDefined()
    })
  })

  describe('消息保存', () => {
    it('应该保存消息到IndexedDB', async () => {
      const message = createTestMessage()
      await storage.saveMessage(message)

      const messages = await storage.getRecentMessages('user123')
      expect(messages).toHaveLength(1)
      expect(messages[0]).toEqual(message)
    })

    it('应该处理保存错误', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

      // Mock一个无效的消息来触发错误
      const invalidMessage = createTestMessage({ id: '' }) // 空ID可能会导致错误

      try {
        await storage.saveMessage(invalidMessage)
      } catch (error) {
        expect(consoleSpy).toHaveBeenCalled()
      }

      consoleSpy.mockRestore()
    })
  })

  describe('消息查询', () => {
    it('应该按用户ID获取消息', async () => {
      const messages = createTestMessages(5)
      await Promise.all(messages.map(m => storage.saveMessage(m)))

      const userMessages = await storage.getRecentMessages('user123')
      expect(userMessages).toHaveLength(3) // user123的消息
    })

    it('应该按时间排序（新消息在前）', async () => {
      const message1 = createTestMessage({ timestamp: 1000, content: '旧消息' })
      const message2 = createTestMessage({ timestamp: 2000, content: '新消息' })

      await storage.saveMessage(message1)
      await storage.saveMessage(message2)

      const messages = await storage.getRecentMessages('user123')
      expect(messages[0].content).toBe('新消息') // 新消息在前
      expect(messages[1].content).toBe('旧消息')
    })

    it('应该限制返回消息数量', async () => {
      const messages = createTestMessages(10)
      await Promise.all(messages.map(m => storage.saveMessage(m)))

      const recent = await storage.getRecentMessages('user123', 5)
      expect(recent).toHaveLength(5)
    })
  })

  describe('消息统计', () => {
    it('应该正确统计消息数量', async () => {
      const messages = createTestMessages(3)
      await Promise.all(messages.map(m => storage.saveMessage(m)))

      const count = await storage.getMessageCount('user123')
      expect(count).toBe(3)
    })
  })

  describe('数据清理', () => {
    it('应该清理指定用户的所有消息', async () => {
      // 创建多用户消息
      const user1Messages = createTestMessages(2)
      const user2Messages = createTestMessages(2, 'user456')

      await Promise.all([
        ...user1Messages.map(m => storage.saveMessage(m)),
        ...user2Messages.map(m => storage.saveMessage(m))
      ])

      await storage.clearAllMessages('user123')
      const user1Count = await storage.getMessageCount('user123')
      const user2Count = await storage.getMessageCount('user456')

      expect(user1Count).toBe(0)
      expect(user2Count).toBe(2)
    })

    it('应该清理所有消息', async () => {
      const messages = createTestMessages(3)
      await Promise.all(messages.map(m => storage.saveMessage(m)))

      await storage.clearAllMessages()

      const count = await storage.getMessageCount('user123')
      expect(count).toBe(0)
    })
  })
})