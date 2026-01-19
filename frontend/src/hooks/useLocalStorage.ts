// frontend/src/hooks/useLocalStorage.ts
import { useState, useEffect } from 'react'

export function useLocalStorage<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  // 初始化时从localStorage读取
  const [value, setValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(`shadow_writing_${key}`)
      return item ? JSON.parse(item) : defaultValue
    } catch (error) {
      console.error('Failed to load from localStorage:', error)
      return defaultValue
    }
  })

  // 更新函数（支持函数式更新）
  const setStoredValue = (newValue: T | ((prev: T) => T)) => {
    setValue(prev => {
      const valueToStore = newValue instanceof Function ? newValue(prev) : newValue
      try {
        localStorage.setItem(`shadow_writing_${key}`, JSON.stringify(valueToStore))
      } catch (error) {
        console.error('Failed to save to localStorage:', error)
      }
      return valueToStore
    })
  }

  // 删除函数
  const removeStoredValue = () => {
    try {
      localStorage.removeItem(`shadow_writing_${key}`)
    } catch (error) {
      console.error('Failed to remove from localStorage:', error)
    }
    setValue(defaultValue)
  }

  return [value, setStoredValue, removeStoredValue]
}
