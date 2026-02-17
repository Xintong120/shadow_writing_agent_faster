// frontend/src/types/learning.ts
// 学习相关类型定义

// 练习项目数据结构
export interface LearningItem {
  id: number
  original: string // 原文句子
  mimic: string // AI 模仿句子
  mapping: Array<{
    from: string // 原文词汇
    to: string // 模仿词汇
    category?: string // 词汇类别 (如 Activity_Context, Unexpected_Event 等)
  }>
}

// 学习会话数据
export interface LearningSession {
  talkId: number
  title: string
  items: LearningItem[]
}

// 练习状态
export interface PracticeState {
  inputs: string[] // 用户输入的句子列表
  isExpanded: boolean // 是否展开词汇映射
}