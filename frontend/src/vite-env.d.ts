/// <reference types="vite/client" />

// Electron API 类型定义
interface ElectronAPI {
  getAppVersion(): Promise<string>
  getPlatform(): Promise<string>
  minimizeWindow(): Promise<void>
  maximizeWindow(): Promise<void>
  closeWindow(): Promise<void>
  openDevTools(): Promise<void>

  // 存储管理API
  getStorageInfo(): Promise<{
    localStorageSize: number
    appDataSize: number
    totalSize: number
    userDataPath: string
    localStoragePath: string
    appDataPath: string
  }>
  clearStorage(options?: {
    clearLocalStorage?: boolean
    clearAppData?: boolean
    clearAll?: boolean
  }): Promise<{
    localStorageCleared: boolean
    appDataCleared: boolean
    errors: string[]
  }>

  // 文件系统API
  readFile(filename: string): Promise<any>
  writeFile(filename: string, data: any): Promise<boolean>
  deleteFile(filename: string): Promise<boolean>
  listFiles(subdir?: string): Promise<Array<{
    name: string
    path: string
    size: number
    isDirectory: boolean
    modified: string
  }>>

  // 事件监听
  on(channel: string, callback: (...args: any[]) => void): void
  removeAllListeners(channel: string): void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
    env?: {
      NODE_ENV?: string
      platform?: string
    }
  }
}
