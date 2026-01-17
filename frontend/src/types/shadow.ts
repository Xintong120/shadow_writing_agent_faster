export interface ShadowWritingResult {
  tedTitle: string
  speaker: string
  original: string
  imitation: string  // 匹配后端字段名（后端用 imitation）
  map: Record<string, string[]>  // 匹配后端格式：{ "Concept": ["Leadership", "Management"] }
  paragraph: string
  quality_score?: number  // 质量评分（0-8）
}

/**
 * 前端高亮映射（从后端 map 转换而来）
 * 用于 UI 显示彩色高亮效果
 */
export interface HighlightMapping {
  category: string  // 类别名称（如 "Concept"）
  original: string[]  // 原始词汇列表
  imitation: string[]  // 改写词汇列表
  color: string  // 高亮颜色（前端生成）
}