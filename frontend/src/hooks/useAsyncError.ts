// 异步错误处理Hook
import { useState, useCallback } from 'react'

export function useAsyncError() {
  const [, setError] = useState()
  return useCallback((error: Error) => {
    setError(() => { throw error })
  }, [])
}

