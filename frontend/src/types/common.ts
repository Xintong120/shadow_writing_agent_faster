/**
 * 分页状态
 */
export interface PaginationState {
  currentPage: number
  totalPages: number
  pageSize: number
}

/**
 * 过滤状态
 */
export interface FilterState {
  searchQuery: string
  sortBy: 'date' | 'title' | 'progress'
  sortOrder: 'asc' | 'desc'
}

/**
 * 消息类型
 */
export interface Message {
  id: string
  userId: string
  role: 'user' | 'agent'
  content: string
  timestamp: number
  type?: 'text' | 'ted_results'
}