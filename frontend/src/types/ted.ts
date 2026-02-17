// frontend/src/types/ted.ts
// TED演讲相关类型定义

// TED演讲数据结构（前端显示用）
export interface TedTalk {
  id: number
  title: string
  speaker: string
  duration: string
  views: string
  description: string
  thumbnail: string
  url?: string
}

// TED基本信息（后端数据结构）
export interface TEDInfo {
  title: string
  speaker: string
  url: string
  duration: string      // "12:30"
  views: string         // "1.2M"
  description: string
  relevance_score: number  // 0-1
  thumbnailUrl?: string    // 缩略图URL（可选）
}

// TED候选演讲（搜索结果）
export interface TEDCandidate extends TEDInfo {
  reasons: string[]     // 相关性理由
}

// 搜索状态
export type SearchStatus = 'idle' | 'searching' | 'results'
