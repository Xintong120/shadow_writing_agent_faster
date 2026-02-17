// frontend/src/types/navigation.ts
// 导航菜单项类型定义

import { LucideIcon } from 'lucide-react'

// 导航菜单项接口
export interface NavMenuItem {
  id: string // 唯一标识符
  icon: LucideIcon // Lucide 图标组件
  label: string // 显示标签
}

// 激活标签类型
export type ActiveTab = 'chat' | 'history' | 'downloads' | 'vocab' | 'stats' | 'settings'