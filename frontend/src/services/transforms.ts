import type { TaskStatusResponse, StatsResponse, FlatStats } from '@/types/api'
import type { ShadowWritingResult, HighlightMapping, LearningRecord } from '@/types'

/**
 * 转换后端嵌套统计为扁平化格式
 */
function flattenStats(stats: StatsResponse): FlatStats {
  return {
    total_records: stats.learning_records.total_records,
    total_teds_watched: stats.ted_history.total_watched,
    total_searches: stats.search_history.total_searches,
    avg_quality_score: stats.learning_records.avg_quality_score,
    top_tags: stats.learning_records.top_tags,
    recent_activity: stats.learning_records.recent_activity,
  }
}

/**
 * 生成均匀分布的颜色（HSL色相环）
 */
function generateColors(count: number): string[] {
  const hueStep = 360 / count
  return Array.from({ length: count }, (_, i) => {
    const hue = i * hueStep
    return `hsl(${hue}, 60%, 90%)`  // 柔和的背景色
  })
}

/**
 * 转换后端 map 为前端 HighlightMapping 数组
 */
function convertMapToHighlightMapping(
  map: Record<string, string[]>
): HighlightMapping[] {
  const categories = Object.keys(map)
  const colors = generateColors(categories.length)

  return categories.map((category, index) => {
    const items = map[category] || []
    const half = Math.ceil(items.length / 2)
    const original = items.slice(0, half)
    const imitation = items.slice(half)

    return {
      category,
      original,
      imitation,
      color: colors[index],
    }
  })
}

/**
 * 扁平化批量处理结果
 *
 * 后端按TED分组返回结果，前端需要扁平化为单一数组用于翻页浏览
 *
 * 后端结构：
 * {
 *   results: [
 *     { url: "ted1", ted_info: {...}, results: [r1, r2, ...] },
 *     { url: "ted2", ted_info: {...}, results: [r3, r4, ...] }
 *   ]
 * }
 *
 * 前端需要：
 * [
 *   { tedTitle: "...", speaker: "...", original: "...", ... },
 *   { tedTitle: "...", speaker: "...", original: "...", ... },
 *   ...
 * ]
 */
function flattenBatchResults(taskData: TaskStatusResponse): ShadowWritingResult[] {
  if (!taskData.results || taskData.results.length === 0) {
    return []
  }

  return taskData.results.flatMap((urlResult: any) => {
    const tedInfo = urlResult.ted_info || {}

    return (urlResult.results || []).map((shadowResult: any) => ({
      ...shadowResult,
      tedTitle: tedInfo.title || 'Unknown',
      speaker: tedInfo.speaker || 'Unknown',
      tedUrl: urlResult.url || '',
    }))
  })
}

/**
 * 计算学习时长（估算）
 *
 * 后端不提供学习时长，前端根据记录数估算
 * 假设：每个 Shadow Writing 结果学习2分钟
 */
function calculateLearningTime(records: LearningRecord[]): number {
  const MINUTES_PER_RECORD = 2
  return records.length * MINUTES_PER_RECORD
}

/**
 * 计算连续打卡天数
 *
 * 后端不提供打卡统计，前端根据 learned_at 时间戳计算
 */
function calculateStreakDays(learnedAtDates: string[]): number {
  if (!learnedAtDates || learnedAtDates.length === 0) {
    return 0
  }

  // 转换为日期对象并排序（最新的在前）
  const dates = learnedAtDates
    .map(d => new Date(d).toDateString())
    .filter((v, i, arr) => arr.indexOf(v) === i) // 去重
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())

  let streak = 1
  const today = new Date().toDateString()

  // 如果今天没学习，从昨天开始算
  let currentDate = dates[0] === today
    ? new Date()
    : new Date(Date.now() - 86400000)

  for (let i = 0; i < dates.length; i++) {
    const recordDate = new Date(dates[i])
    const expectedDate = new Date(currentDate.getTime() - i * 86400000)

    if (recordDate.toDateString() === expectedDate.toDateString()) {
      streak++
    } else {
      break
    }
  }

  return streak
}

// ============ LearningItem 相关转换 ============

/**
 * 将 ShadowWritingResult[] 转换为 LearningItem[]
 *
 * 用于 LearningSessionPage 从 mock 数据切换到真实后端数据
 */
function convertShadowResultsToLearningItems(
  shadowResults: ShadowWritingResult[]
): import('@/types/learning').LearningItem[] {
  return shadowResults.map((result, index) => ({
    id: index + 1, // 使用数组索引作为ID
    original: result.original,
    mimic: result.imitation, // ShadowWritingResult 用 imitation
    mapping: convertMapToLearningMapping(result.map), // 转换map格式
  }))
}

/**
 * 将 ShadowWritingResult.map 转换为 LearningItem.mapping 格式
 *
 * 输入: Record<string, string[]> 如 {"Concept": ["Leadership", "Management"]}
 * 输出: Array<{from: string, to: string}> 如 [{from: "Leadership", to: "Management"}]
 */
function convertMapToLearningMapping(
  map: Record<string, string[]>
): Array<{from: string, to: string}> {
  const mappings: Array<{from: string, to: string}> = []

  Object.values(map).forEach(items => {
    // 假设偶数索引是原文词汇，奇数索引是改写词汇
    for (let i = 0; i < items.length; i += 2) {
      if (i + 1 < items.length) {
        mappings.push({
          from: items[i],
          to: items[i + 1],
        })
      }
    }
  })

  return mappings
}

// ============ 导出所有转换工具 ============

export {
  flattenStats,
  generateColors,
  convertMapToHighlightMapping,
  flattenBatchResults,
  calculateLearningTime,
  calculateStreakDays,
  convertShadowResultsToLearningItems,
  convertMapToLearningMapping,
}
