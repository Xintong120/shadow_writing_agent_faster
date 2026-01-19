// 存储服务
class Storage {
  private prefix = 'shadow_writing_'
  
  set<T>(key: string, value: T): void {
    try {
      const serialized = JSON.stringify(value)
      localStorage.setItem(this.prefix + key, serialized)
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
    }
  }
  
  get<T>(key: string, defaultValue?: T): T | undefined {
    try {
      const item = localStorage.getItem(this.prefix + key)
      return item ? JSON.parse(item) : defaultValue
    } catch (error) {
      console.error('Failed to load from localStorage:', error)
      return defaultValue
    }
  }
  
  remove(key: string): void {
    localStorage.removeItem(this.prefix + key)
  }
  
  clear(): void {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(this.prefix)) {
        localStorage.removeItem(key)
      }
    })
  }
  
  has(key: string): boolean {
    return localStorage.getItem(this.prefix + key) !== null
  }
}

export const storage = new Storage()

