import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatInterface from '@/components/organisms/ChatInterface'
import { createTestMessage, createTestMessages } from '@/test-utils/test-helpers'

const defaultProps = {
  messages: [],
  tedCandidates: [],
  selectedUrls: [],
  recentSearches: [],
  onSendMessage: vi.fn(),
  onToggleTED: vi.fn(),
  onStartBatch: vi.fn(),
  onClearSelection: vi.fn(),
  isTyping: false,
  isSearching: false,
  className: ''
}

describe('ChatInterface Loading States', () => {
  it('应该显示加载历史消息的UI', () => {
    render(<ChatInterface {...defaultProps} isLoadingHistory={true} messages={[]} />)

    expect(screen.getByText('正在加载聊天记录...')).toBeInTheDocument()

    // 检查是否有加载动画（旋转图标）
    const loadingElement = screen.getByText('正在加载聊天记录...').parentElement
    expect(loadingElement).toHaveClass('animate-spin')
  })

  it('加载完成后应该显示消息列表', () => {
    const messages = [createTestMessage()]
    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={messages} />)

    expect(screen.queryByText('正在加载聊天记录...')).not.toBeInTheDocument()
    expect(screen.getByText(messages[0].content)).toBeInTheDocument()
  })

  it('应该正确显示多条消息', () => {
    const messages = createTestMessages(3)
    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={messages} />)

    messages.forEach(message => {
      expect(screen.getByText(message.content)).toBeInTheDocument()
    })
  })

  it('应该显示用户和助手消息的不同样式', () => {
    const userMessage = createTestMessage({ role: 'user', content: '用户消息' })
    const agentMessage = createTestMessage({ role: 'agent', content: '助手消息' })

    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={[userMessage, agentMessage]} />)

    expect(screen.getByText('用户消息')).toBeInTheDocument()
    expect(screen.getByText('助手消息')).toBeInTheDocument()
  })

  it('正在输入状态时应该显示输入指示器', () => {
    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={[]} isTyping={true} />)

    expect(screen.getByText('正在搜索...')).toBeInTheDocument()
  })

  it('首次使用时应该显示快速建议', () => {
    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={[]} />)

    expect(screen.getByText('# 人工智能')).toBeInTheDocument()
    expect(screen.getByText('# 领导力')).toBeInTheDocument()
  })

  it('有消息后不应该显示快速建议', () => {
    const messages = [createTestMessage()]
    render(<ChatInterface {...defaultProps} isLoadingHistory={false} messages={messages} />)

    expect(screen.queryByText('# 人工智能')).not.toBeInTheDocument()
  })

  it('应该正确传递props给子组件', () => {
    const mockOnSendMessage = vi.fn()
    const mockOnToggleTED = vi.fn()
    const mockOnStartBatch = vi.fn()
    const mockOnClearSelection = vi.fn()

    render(
      <ChatInterface
        {...defaultProps}
        isLoadingHistory={false}
        messages={[]}
        onSendMessage={mockOnSendMessage}
        onToggleTED={mockOnToggleTED}
        onStartBatch={mockOnStartBatch}
        onClearSelection={mockOnClearSelection}
      />
    )

    // 验证组件渲染成功
    expect(screen.getByText('Shadow Writing Agent')).toBeInTheDocument()
  })
})