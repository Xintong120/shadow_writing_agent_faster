/**
 * 搜索历史集成自动化测试套件
 *
 * 测试SearchPage组件的基本渲染和localStorage持久化
 */

import { render, screen, waitFor } from '@testing-library/react'
import { MantineProvider } from '@mantine/core'
import SearchPage from '@/pages/SearchPage'

// 测试组件包装器
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MantineProvider defaultColorScheme="light">
    {children}
  </MantineProvider>
)

describe('搜索历史集成自动化测试套件', () => {
  beforeEach(() => {
    // 清理localStorage
    localStorage.clear()
  })

  afterEach(() => {
    // 清理测试数据
    localStorage.clear()
  })

  test('SearchPage应该能够正常渲染', async () => {
    render(
      <TestWrapper>
        <SearchPage />
      </TestWrapper>
    )

    // 等待初始加载完成
    await waitFor(() => {
      expect(screen.getByText('你好！我是你的英语学习助手。')).toBeInTheDocument()
    })
  })

  test('应该显示搜索输入框', async () => {
    render(
      <TestWrapper>
        <SearchPage />
      </TestWrapper>
    )

    // 等待组件加载
    await waitFor(() => {
      expect(screen.getByText('你好！我是你的英语学习助手。')).toBeInTheDocument()
    })

    // 验证输入框存在
    const input = screen.getByPlaceholderText(/告诉我你想搜索或者学习的TED演讲主题/)
    expect(input).toBeInTheDocument()
  })

  test('应该正确处理localStorage中的搜索结果数据', () => {
    // 预设localStorage数据
    const searchData = [['人工智能', [
      {
        title: '人工智能的未来',
        speaker: '李教授',
        url: 'https://ted.com/talks/ai_future',
        duration: '15:30',
        views: '2.1M',
        description: '探讨人工智能的发展方向',
        relevance_score: 0.95,
        reasons: ['高度相关']
      }
    ]]]
    localStorage.setItem('ted_search_results', JSON.stringify(searchData))

    render(
      <TestWrapper>
        <SearchPage />
      </TestWrapper>
    )

    // 验证localStorage数据被正确设置
    const saved = localStorage.getItem('ted_search_results')
    expect(saved).not.toBeNull()

    const parsed = JSON.parse(saved!)
    expect(parsed).toHaveLength(1)
    expect(parsed[0][0]).toBe('人工智能')
    expect(parsed[0][1]).toHaveLength(1)
  })

  test('应该处理localStorage中的无效数据而不崩溃', async () => {
    // 设置无效的JSON数据
    localStorage.setItem('ted_search_results', 'invalid json data')

    // Mock console.error
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <TestWrapper>
        <SearchPage />
      </TestWrapper>
    )

    // 等待组件加载
    await waitFor(() => {
      expect(screen.getByText('你好！我是你的英语学习助手。')).toBeInTheDocument()
    })

    // 验证错误被记录
    expect(consoleSpy).toHaveBeenCalled()

    consoleSpy.mockRestore()
  })
})
