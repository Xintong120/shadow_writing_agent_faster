import type { Message } from '@/types'

/**
 * 创建测试消息
 */
export const createTestMessage = (overrides: Partial<Message> = {}): Message => ({
  id: `msg_${Date.now()}_${Math.random()}`,
  userId: 'user123',
  role: 'user' as const,
  content: '测试消息',
  timestamp: Date.now(),
  type: 'text' as const,
  ...overrides
})

/**
 * 创建多个测试消息
 */
export const createTestMessages = (count: number, userId = 'user123'): Message[] => {
  return Array.from({ length: count }, (_, i) =>
    createTestMessage({
      content: `消息 ${i + 1}`,
      id: `msg_${Date.now()}_${i}`,
      role: i % 2 === 0 ? 'user' : 'agent'
    })
  )
}

/**
 * 创建不同用户的测试消息
 */
export const createMultiUserMessages = (): Message[] => {
  return [
    createTestMessage({ content: '用户1消息1', role: 'user' }),
    createTestMessage({ content: '用户1消息2', role: 'agent' }),
    createTestMessage({ content: '用户2消息1', role: 'user' }),
    createTestMessage({ content: '用户2消息2', role: 'agent' }),
  ]
}

/**
 * Mock IndexedDB成功操作
 */
export const mockIndexedDBSuccess = () => {
  // 使用 fake-indexeddb 自动处理
}

/**
 * Mock IndexedDB错误
 */
export const mockIndexedDBError = () => {
  const originalOpen = indexedDB.open
  indexedDB.open = jest.fn().mockImplementation(() => {
    throw new Error('IndexedDB error')
  })
}

/**
 * Mock慢速IndexedDB操作（用于测试加载状态）
 */
export const mockSlowIndexedDB = () => {
  // 可以在这里添加延迟逻辑
}

/**
 * 等待一段时间的工具函数
 */
export const wait = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 清理IndexedDB测试数据
 */
export const cleanupTestDB = async () => {
  // 在测试结束后清理
}