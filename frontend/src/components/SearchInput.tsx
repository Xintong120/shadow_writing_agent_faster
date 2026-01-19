// frontend/src/components/SearchInput.tsx
// 搜索输入组件 - 包含输入框、提交按钮、加载状态和热门标签

import { useState } from 'react'
import { Search, ArrowRight } from 'lucide-react'

interface SearchInputProps {
  onSearch: (query: string) => void
  isSearching: boolean
}

const SearchInput = ({ onSearch, isSearching }: SearchInputProps) => {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query)
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="relative group" role="search">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          {isSearching ? (
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-indigo-500 border-t-transparent"></div>
          ) : (
            <Search className="h-5 w-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入学习主题，例如 'AI Ethics'..."
          className="w-full pl-12 pr-4 py-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-lg placeholder:text-slate-400 dark:placeholder:text-slate-500 text-slate-900 dark:text-white"
        />
        <button
          type="submit"
          className="absolute right-2 top-2 bottom-2 bg-slate-900 dark:bg-indigo-600 text-white px-4 rounded-xl font-medium hover:bg-slate-800 dark:hover:bg-indigo-700 transition-colors disabled:opacity-50"
          disabled={!query.trim() || isSearching}
        >
          <span className="hidden sm:inline">开始探索</span>
          <ArrowRight className="sm:hidden" size={20} />
        </button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2 justify-center text-sm text-slate-500 dark:text-slate-400">
        <span>热门搜索:</span>
        {["Public Speaking", "Technology", "Psychology"].map(tag => (
          <button
            key={tag}
            onClick={() => setQuery(tag)}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 underline decoration-dotted transition-colors"
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  )
}

export default SearchInput