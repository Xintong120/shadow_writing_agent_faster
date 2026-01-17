// frontend/src/components/LearningCard.tsx
// 学习卡片组件 - 包含原文、模仿和用户练习区域

import { useState } from 'react'
import { Sparkles, ChevronUp, ChevronDown, PenTool, Plus, Check } from 'lucide-react'
import { LearningItem } from '@/types/learning'

interface LearningCardProps {
  data: LearningItem
}

const LearningCard = ({ data }: LearningCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [userInputs, setUserInputs] = useState<string[]>([''])

  // 添加新的输入框
  const handleAddInput = () => {
    setUserInputs([...userInputs, ''])
  }

  // 更新输入框内容
  const handleInputChange = (index: number, value: string) => {
    const newInputs = [...userInputs]
    newInputs[index] = value
    setUserInputs(newInputs)
  }

  return (
    <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden mb-6 shadow-sm hover:shadow-md transition-all duration-300 group">
      {/* 1. Original Sentence (Immersive Header) */}
      <div className="p-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Original</span>
        </div>
        <p className="text-xl sm:text-2xl font-serif text-slate-800 dark:text-slate-100 leading-relaxed italic">
          "{data.original}"
        </p>
      </div>

      {/* 2. AI Mimic (Reference) */}
      <div className="p-6 border-b border-slate-100 dark:border-slate-700 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 mb-2">
               <Sparkles size={14} className="text-indigo-500" />
               <span className="text-xs font-bold text-indigo-500 uppercase tracking-wider">AI Mimic</span>
            </div>
            <p className="text-lg text-slate-700 dark:text-slate-200 font-medium">
              "{data.mimic}"
            </p>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors p-1"
            title="查看词汇映射"
          >
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
        </div>

        {/* 词汇映射 (折叠区域) */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700 animate-in slide-in-from-top-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {data.mapping.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm bg-slate-50 dark:bg-slate-900/50 p-2 rounded border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-500 dark:text-slate-400">{item.from}</span>
                  <svg className="w-4 h-4 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400">{item.to}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 3. User Practice Area (Interactive) */}
      <div className="p-6 bg-white dark:bg-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <PenTool size={14} className="text-emerald-500" />
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Your Practice</span>
        </div>

        <div className="space-y-3">
          {userInputs.map((input, idx) => (
            <div key={idx} className="relative group/input animate-in fade-in slide-in-from-bottom-2">
              <input
                type="text"
                value={input}
                onChange={(e) => handleInputChange(idx, e.target.value)}
                placeholder="在此输入你的模仿句子..."
                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg pl-4 pr-10 py-3 text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition-all placeholder:text-slate-400"
              />
              <div className="absolute right-3 top-3 opacity-0 group-focus-within/input:opacity-100 transition-opacity">
                {input.length > 0 ? <Check size={18} className="text-emerald-500" /> : <span className="w-4"></span>}
              </div>
            </div>
          ))}

          <button
            onClick={handleAddInput}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400 font-medium px-2 py-1 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <Plus size={16} />
            <span>添加另一句模仿</span>
          </button>
        </div>
      </div>
    </section>
  )
}

export default LearningCard