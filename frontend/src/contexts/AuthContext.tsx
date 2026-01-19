// frontend/src/contexts/AuthContext.tsx
// 全局认证状态管理 - 使用 React Context 模式管理应用的登录状态

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

// 定义认证状态的类型：未登录、用户登录、访客模式
export type AuthStatus = 'logged_out' | 'user' | 'guest'

// 认证上下文的接口定义，包含状态和操作方法
export interface AuthContextType {
  authStatus: AuthStatus // 当前认证状态
  login: (mode: 'user' | 'guest') => void // 登录方法，接受用户类型
  logout: () => void // 退出登录方法
}

// 创建认证上下文，初始值为 undefined
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// AuthProvider 组件的属性接口
interface AuthProviderProps {
  children: ReactNode // 子组件
}

// 认证提供者组件 - 包装整个应用，提供认证状态管理
export function AuthProvider({ children }: AuthProviderProps) {
  // 使用 useState 管理认证状态，初始状态为 'logged_out'
  const [authStatus, setAuthStatus] = useState<AuthStatus>('logged_out')

  // 登录方法 - 使用 useCallback 优化性能，设置认证状态
  const login = useCallback((mode: 'user' | 'guest') => {
    setAuthStatus(mode)
  }, [])

  // 退出登录方法 - 重置为未登录状态
  const logout = useCallback(() => {
    setAuthStatus('logged_out')
  }, [])

  // 返回 Provider 组件，value 包含所有认证相关的状态和方法
  return (
    <AuthContext.Provider value={{
      authStatus,
      login,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  )
}

// 自定义 hook - 提供便捷的认证上下文访问方式
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  // 如果在 AuthProvider 外部使用，抛出错误
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}