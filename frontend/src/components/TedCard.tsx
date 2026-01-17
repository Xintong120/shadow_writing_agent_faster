// frontend/src/components/TedCard.tsx
// TED演讲卡片组件 - 可选择状态，支持悬停和点击交互

import { Play, CheckCircle } from 'lucide-react'
import { TedTalk } from '@/types/ted'

interface TedCardProps {
  talk: TedTalk
  isSelected: boolean
  onToggle: (id: number) => void
}

const TedCard = ({ talk, isSelected, onToggle }: TedCardProps) => {
  return (
    <article
      onClick={() => onToggle(talk.id)}
      className={`relative group cursor-pointer bg-white dark:bg-slate-800 rounded-2xl overflow-hidden border transition-all duration-300 flex flex-col h-full ${
        isSelected
          ? 'border-indigo-500 ring-2 ring-indigo-500/20 shadow-lg translate-y-[-2px]'
          : 'border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-500/50 hover:shadow-md'
      }`}
    >
      <div className={`h-36 sm:h-40 ${talk.thumbnail} flex items-center justify-center relative overflow-hidden`}>
        <div className="absolute inset-0 bg-black/5 dark:bg-black/20 group-hover:bg-transparent transition-colors"></div>
        <div className="w-12 h-12 bg-white/30 backdrop-blur-md rounded-full flex items-center justify-center z-10 shadow-lg group-hover:scale-110 transition-transform">
          <Play className="text-slate-900 fill-slate-900 ml-1" size={20} />
        </div>
        <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-sm text-white text-xs font-bold px-2 py-1 rounded">
          {talk.duration}
        </div>
      </div>

      <div className="p-4 flex flex-col flex-1">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-bold text-slate-900 dark:text-white line-clamp-2 leading-tight text-base">
            {talk.title}
          </h3>
          {isSelected && (
            <CheckCircle className="text-indigo-600 dark:text-indigo-400 flex-shrink-0 ml-2 animate-in zoom-in" size={20} />
          )}
        </div>
        <p className="text-sm text-indigo-600 dark:text-indigo-400 font-medium mb-2">{talk.speaker}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-4 flex-1">
          {talk.description}
        </p>
      </div>
    </article>
  )
}

export default TedCard