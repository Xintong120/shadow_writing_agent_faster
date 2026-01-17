// frontend/src/services/fileStorage.ts
// 通用文件存储服务 - 用于大数据存储

export interface FileStorageOptions {
  subdir?: string // 子目录
  autoCreateDir?: boolean // 自动创建目录
}

// 文件存储服务类
class FileStorage {
  private isElectron(): boolean {
    return typeof window !== 'undefined' && !!window.electronAPI
  }

  // 读取文件
  async read<T = any>(filename: string, options: FileStorageOptions = {}): Promise<T | null> {
    if (!this.isElectron()) {
      console.warn('File storage only available in Electron environment')
      return null
    }

    try {
      const filepath = options.subdir ? `${options.subdir}/${filename}` : filename
      return await window.electronAPI!.readFile(filepath)
    } catch (error) {
      console.error('Failed to read file:', error)
      return null
    }
  }

  // 写入文件
  async write(filename: string, data: any, options: FileStorageOptions = {}): Promise<boolean> {
    if (!this.isElectron()) {
      console.warn('File storage only available in Electron environment')
      return false
    }

    try {
      const filepath = options.subdir ? `${options.subdir}/${filename}` : filename
      return await window.electronAPI!.writeFile(filepath, data)
    } catch (error) {
      console.error('Failed to write file:', error)
      return false
    }
  }

  // 删除文件
  async delete(filename: string, options: FileStorageOptions = {}): Promise<boolean> {
    if (!this.isElectron()) {
      console.warn('File storage only available in Electron environment')
      return false
    }

    try {
      const filepath = options.subdir ? `${options.subdir}/${filename}` : filename
      return await window.electronAPI!.deleteFile(filepath)
    } catch (error) {
      console.error('Failed to delete file:', error)
      return false
    }
  }

  // 列出文件
  async list(options: FileStorageOptions = {}): Promise<Array<{
    name: string
    path: string
    size: number
    isDirectory: boolean
    modified: string
  }>> {
    if (!this.isElectron()) {
      console.warn('File storage only available in Electron environment')
      return []
    }

    try {
      return await window.electronAPI!.listFiles(options.subdir)
    } catch (error) {
      console.error('Failed to list files:', error)
      return []
    }
  }

  // 检查文件是否存在
  async exists(filename: string, options: FileStorageOptions = {}): Promise<boolean> {
    if (!this.isElectron()) {
      return false
    }

    try {
      const files = await this.list(options)
      return files.some(file => file.name === filename)
    } catch (error) {
      console.error('Failed to check file existence:', error)
      return false
    }
  }

  // 获取存储信息
  async getStorageInfo() {
    if (!this.isElectron()) {
      return {
        localStorageSize: 0,
        appDataSize: 0,
        totalSize: 0,
        userDataPath: '',
        localStoragePath: '',
        appDataPath: ''
      }
    }

    try {
      return await window.electronAPI!.getStorageInfo()
    } catch (error) {
      console.error('Failed to get storage info:', error)
      return {
        localStorageSize: 0,
        appDataSize: 0,
        totalSize: 0,
        userDataPath: '',
        localStoragePath: '',
        appDataPath: ''
      }
    }
  }

  // 清理存储
  async clearStorage(options: {
    clearLocalStorage?: boolean
    clearAppData?: boolean
    clearAll?: boolean
  } = {}) {
    if (!this.isElectron()) {
      return {
        localStorageCleared: false,
        appDataCleared: false,
        errors: ['File storage only available in Electron environment']
      }
    }

    try {
      return await window.electronAPI!.clearStorage(options)
    } catch (error) {
      console.error('Failed to clear storage:', error)
      return {
        localStorageCleared: false,
        appDataCleared: false,
        errors: [error.message]
      }
    }
  }
}

// 导出单例实例
export const fileStorage = new FileStorage()

// 便捷方法
export const tedStorage = {
  // TED内容存储
  async saveTedContent(talkId: string, content: any) {
    return await fileStorage.write(`ted_${talkId}.json`, content, { subdir: 'ted-content' })
  },

  async getTedContent(talkId: string) {
    return await fileStorage.read(`ted_${talkId}.json`, { subdir: 'ted-content' })
  },

  async deleteTedContent(talkId: string) {
    return await fileStorage.delete(`ted_${talkId}.json`, { subdir: 'ted-content' })
  }
}

export const learningStorage = {
  // 学习记录存储
  async saveLearningRecord(recordId: string, record: any) {
    return await fileStorage.write(`learning_${recordId}.json`, record, { subdir: 'learning-records' })
  },

  async getLearningRecord(recordId: string) {
    return await fileStorage.read(`learning_${recordId}.json`, { subdir: 'learning-records' })
  },

  async listLearningRecords() {
    return await fileStorage.list({ subdir: 'learning-records' })
  }
}
