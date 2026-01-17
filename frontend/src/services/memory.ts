import { fetchAPI } from './client'
import { handleError } from '@/utils/errorHandler'
import type {
  GetLearningRecordsRequest,
  GetLearningRecordsResponse,
  StatsResponse,
} from '@/types/api'

// ============ Memory 系统相关 ============

export const getLearningRecords = async (
  userId: string,
  filters?: Omit<GetLearningRecordsRequest, 'user_id'>
) => {
  const params = new URLSearchParams({
    ...filters,
    limit: String(filters?.limit || 20),
    offset: String(filters?.offset || 0),
  } as any)

  const response = await fetchAPI<GetLearningRecordsResponse>(
    `/memory/learning-records/${userId}?${params}`,
    { method: 'GET' }
  )

  if (!response.success) {
    handleError(new Error(response.error || '获取学习记录失败'), 'getLearningRecords')
    throw new Error(response.error || '获取学习记录失败')
  }

  return response.data
}

export const getStats = async (userId: string) => {
  const response = await fetchAPI<StatsResponse>(`/memory/stats/${userId}`, {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取统计数据失败'), 'getStats')
    throw new Error(response.error || '获取统计数据失败')
  }

  return response.data
}

// ============ 导出 Memory API ============

export const memoryApi = {
  getLearningRecords,
  getStats,
}

export default memoryApi