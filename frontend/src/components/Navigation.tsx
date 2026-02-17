// frontend/src/components/Navigation.tsx
// 导航栏组件 - 包含桌面侧边栏和移动端底部导航

import {
  MessageSquare,
  Library,
  Download,
  BarChart2,
  Settings,
  LogOut,
  Sparkles,
  Book,
} from 'lucide-react';
import { NavMenuItem, ActiveTab } from '@/types/navigation';

// 导航菜单项配置
const menuItems: NavMenuItem[] = [
  { id: 'chat', icon: MessageSquare, label: 'AI 创作' },
  { id: 'history', icon: Library, label: '学习记录' },
  { id: 'downloads', icon: Download, label: '任务队列' },
  { id: 'vocab', icon: Book, label: '生词本' },
  { id: 'stats', icon: BarChart2, label: '数据统计' },
  { id: 'settings', icon: Settings, label: '系统设置' },
];

interface NavigationProps {
  activeTab: ActiveTab
  setActiveTab: (tab: ActiveTab) => void
  userMode: 'user' | 'guest'
  onLogout: () => void
}

const Navigation = ({ activeTab, setActiveTab, userMode, onLogout }: NavigationProps) => {
  return (
    <>
      {/* Desktop Sidebar */}
      <nav
        className="hidden md:flex w-20 lg:w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex-col h-screen flex-shrink-0 transition-all duration-300 z-50"
        aria-label="Main Navigation"
      >
        <div className="p-6 flex items-center justify-center lg:justify-start gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-md shadow-indigo-500/20">
            <Sparkles size={20} className="text-white" />
          </div>
          <span className="font-bold text-xl hidden lg:block tracking-tight text-slate-900 dark:text-white">
            Shadow<span className="text-indigo-600">Writer</span>
          </span>
        </div>

        <div className="flex-1 mt-6 px-4 space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as ActiveTab)}
              className={`w-full flex items-center gap-3 p-3.5 rounded-xl transition-all duration-200 group ${
                activeTab === item.id
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <item.icon size={22} className={activeTab === item.id ? 'animate-pulse-slow' : 'group-hover:scale-110 transition-transform'} />
              <span className="hidden lg:block font-medium">{item.label}</span>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer group">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-sm font-bold text-white shadow-sm">
              {userMode === 'guest' ? 'G' : 'JD'}
            </div>
            <div className="hidden lg:block flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                {userMode === 'guest' ? 'Guest User' : 'John Doe'}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                {userMode === 'guest' ? 'Trial Version' : 'Premium Member'}
              </p>
            </div>
            <button
              onClick={onLogout}
              className="hidden lg:block p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 pb-safe z-50 flex justify-around p-3">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id as ActiveTab)}
            className={`flex flex-col items-center gap-1 p-2 rounded-xl transition-colors ${
              activeTab === item.id
                ? 'text-indigo-600 dark:text-indigo-400'
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <item.icon size={24} />
            <span className="text-[10px] font-medium">{item.label}</span>
          </button>
        ))}
      </nav>
    </>
  )
}

export default Navigation