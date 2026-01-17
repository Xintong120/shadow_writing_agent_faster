import type { APIResponse } from '@/types'

export async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<APIResponse<T>> {
  return { success: true, data: {} as T }
}
