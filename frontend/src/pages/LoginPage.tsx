// frontend/src/pages/LoginPage.tsx
import { Sparkles, User, Zap } from 'lucide-react'

interface LoginPageProps {
  onLogin: (mode: 'user' | 'guest') => void
}

const LoginPage = ({ onLogin }: LoginPageProps) => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white dark:bg-slate-800 rounded-3xl shadow-xl overflow-hidden p-8 space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="text-center">
          <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-indigo-200 dark:shadow-indigo-900">
            <Sparkles size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-2">Shadow<span className="text-indigo-600 dark:text-indigo-400">Writer</span></h1>
          <p className="text-slate-500 dark:text-slate-400">掌握像 TED 演讲者一样的英语表达</p>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => onLogin('user')}
            className="w-full bg-slate-900 dark:bg-slate-800 text-white font-bold py-4 rounded-xl hover:bg-slate-800 dark:hover:bg-slate-700 transition-all flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
          >
            <User size={20} />
            <span>登录账号</span>
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-slate-200 dark:border-slate-700"></span>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white dark:bg-slate-800 px-2 text-slate-400 dark:text-slate-500">或者</span>
            </div>
          </div>

          <button
            onClick={() => onLogin('guest')}
            className="w-full bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 font-bold py-4 rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-800 transition-all flex items-center justify-center gap-2 border border-indigo-100 dark:border-indigo-800"
          >
            <Zap size={20} />
            <span>免登录试用 (Guest Mode)</span>
          </button>
        </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-500">
          点击登录即代表您同意我们的 <a href="#" className="underline hover:text-indigo-600 dark:hover:text-indigo-400">服务条款</a> 和 <a href="#" className="underline hover:text-indigo-600 dark:hover:text-indigo-400">隐私政策</a>
        </p>
      </div>
    </div>
  )
}

export default LoginPage