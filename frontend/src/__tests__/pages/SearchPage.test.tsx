import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { TaskProvider } from '@/contexts/TaskContext'
import SearchPage from '@/pages/SearchPage'
import { chatStorage } from '@/utils/chatStorage'
import { createTestMessage } from '@/test-utils/test-helpers'

// Mock 依赖
vi.mock('@/contexts/TaskContext', () => ({
  TaskProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useTasks: () => ({
    startSearchTask: vi.fn().mockResolvedValue([]),
    startBatchTask: vi.fn()
  })
}))

vi.mock('@/hooks/useIncompleteTasks', () => ({
  useIncompleteTasks: () => []
}))

vi.mock('@/services/api', () => ({
  api: {
    searchTED: vi.fn().mockResolvedValue({
      candidates: [
        {
          title: 'Test TED Talk',
          speaker: 'Test Speaker',
          url: 'https://ted.com/talks/test',
          duration: '10:00',
          views: '1M',
          description: 'Test description',
          relevance_score: 0.9
        }
      ],
      total: 1
    })
  }
}))

const renderSearchPage = () => {
  return render(
    <BrowserRouter>
      <TaskProvider>
        <SearchPage />
      </TaskProvider>
    </BrowserRouter>
  )
}

describe('SearchPage IndexedDB Integration', () => {
  beforeEach(async () => {
    // 清理测试数据
    await chatStorage.clearAllMessages()
  })

  describe('初始化加载', () => {
    it('首次访问应该创建欢迎消息', async () => {
      renderSearchPage()

      await waitFor(() => {
        expect(screen.getByText(/你好！我是你的英语学习助手/)).toBeInTheDocument()
      })

      // 验证消息已保存到IndexedDB
      const messages = await chatStorage.getRecentMessages('user_123')
      expect(messages).toHaveLength(1)
      expect(messages[0].content).toContain('英语学习助手')
    })

    it('应该从IndexedDB恢复历史消息', async () => {
      // 预先保存消息到IndexedDB
      const testMessage = createTestMessage({ content: '历史消息' })
      await chatStorage.saveMessage(testMessage)

      renderSearchPage()

      await waitFor(() => {
        expect(screen.getByText('历史消息')).toBeInTheDocument()
      })
    })

    it('加载失败时应该显示错误但不崩溃', async () => {
      // Mock IndexedDB错误
      const originalInit = chatStorage.init
      chatStorage.init = vi.fn().mockRejectedValue(new Error('DB Error'))

      renderSearchPage()

      // 应该仍然能正常渲染（显示欢迎消息）
      await waitFor(() => {
        expect(screen.getByText(/你好！我是你的英语学习助手/)).toBeInTheDocument()
      })

      // 恢复原始方法
      chatStorage.init = originalInit
    })
  })

  describe('消息发送', () => {
    it('发送消息应该同时更新UI和IndexedDB', async () => {
      const user = userEvent.setup()
      renderSearchPage()

      const input = screen.getByPlaceholderText(/告诉我你想搜索/)
      await user.type(input, '测试消息')
      await user.keyboard('{Enter}')

      // 验证UI更新
      expect(screen.getByText('测试消息')).toBeInTheDocument()

      // 验证IndexedDB保存
      await waitFor(async () => {
        const messages = await chatStorage.getRecentMessages('user_123')
        expect(messages.some(m => m.content === '测试消息')).toBe(true)
      })
    })

    it('应该处理搜索意图并调用API', async () => {
      const user = userEvent.setup()
      renderSearchPage()

      const input = screen.getByPlaceholderText(/告诉我你想搜索/)
      await user.type(input, '搜索人工智能')
      await user.keyboard('{Enter}')

      // 验证显示搜索状态
      expect(screen.getByText(/正在为你搜索/)).toBeInTheDocument()

      // 等待搜索完成
      await waitFor(() => {
        expect(screen.getByText(/找到了.*个演讲/)).toBeInTheDocument()
      })
    })
  })

  describe('加载状态', () => {
    it('应该显示加载历史消息的状态', async () => {
      // Mock慢速IndexedDB
      const originalInit = chatStorage.init
      chatStorage.init = vi.fn().mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      )

      renderSearchPage()

      // 应该显示加载状态
      expect(screen.getByText('正在加载聊天记录...')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.queryByText('正在加载聊天记录...')).not.toBeInTheDocument()
      })

      // 恢复原始方法
      chatStorage.init = originalInit
    })
  })

  describe('TED搜索结果', () => {
    it('应该显示TED候选列表', async () => {
      const user = userEvent.setup()
      renderSearchPage()

      const input = screen.getByPlaceholderText(/告诉我你想搜索/)
      await user.type(input, '搜索测试')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('Test TED Talk')).toBeInTheDocument()
        expect(screen.getByText('Test Speaker')).toBeInTheDocument()
      })
    })

    it('应该支持TED选择', async () => {
      const user = userEvent.setup()
      renderSearchPage()

      // 触发搜索
      const input = screen.getByPlaceholderText(/告诉我你想搜索/)
      await user.type(input, '搜索测试')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('Test TED Talk')).toBeInTheDocument()
      })

      // 点击选择TED
      const tedCard = screen.getByText('Test TED Talk').closest('div')
      await user.click(tedCard!)

      // 验证选择状态
      expect(screen.getByText('已选择 1 / 1 个演讲')).toBeInTheDocument()
    })
  })
})