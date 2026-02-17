import { useState, useEffect, useCallback } from 'react'
import {
  ArrowRight, MoreHorizontal, ChevronDown, ChevronUp,
  Sparkles, PenTool, Plus, Loader2, Trash2
} from 'lucide-react'
import { toast } from 'sonner'
import dJSON from 'dirty-json'
import { useLearning } from '@/contexts/LearningContext'
import { LearningItem } from '@/types/learning'
import { saveUserPractice, getUserPractice } from '@/services/api'
import { updateHistoryStatus } from '@/services/downloadApi'
import { practiceStorage } from '@/utils/practiceStorage'
import { practiceSync } from '@/utils/practiceSync'
import { useQueryClient } from '@tanstack/react-query'
import { ClickableText } from '@/components/ClickableText'
import { WordPopup } from '@/components/WordPopup'

interface LearningCardProps {
  data: LearningItem
  index: number
  userInputs: string[]
  onChange: (inputs: string[]) => void
  onDelete?: () => void
  onWordClick: (word: string, x: number, y: number) => void
}

interface LearningSessionPageProps {
  onBack?: () => void
}

const LearningCard = ({ data, index, userInputs, onChange, onDelete, onWordClick }: LearningCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleAddInput = () => onChange([...userInputs, ''])
  const handleInputChange = (idx: number, value: string) => {
    const newInputs = [...userInputs]
    newInputs[idx] = value
    onChange(newInputs)
  }

  return (
    <div className="mb-8">
      {/* 练习编号 */}
      <div className="flex items-center gap-4 mb-4">
        <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
        <span className="text-xs font-bold text-slate-400">练习 {index + 1}</span>
        <div className="h-[1px] flex-1 bg-slate-200 dark:bg-slate-800"></div>
      </div>

      {/* 卡片 */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {/* Original */}
        <div className="p-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Original</span>
          </div>
          <p className="text-xl font-serif text-slate-800 dark:text-slate-100 italic leading-relaxed">
            <ClickableText text={data.original} onWordClick={onWordClick} />
          </p>
        </div>

        {/* AI Mimic */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-700">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={14} className="text-indigo-500" />
                <span className="text-xs font-bold text-indigo-500 uppercase tracking-wider">AI Mimic</span>
              </div>
              <p className="text-lg text-slate-700 dark:text-slate-200 font-medium">
                <ClickableText text={data.mimic} onWordClick={onWordClick} />
              </p>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors p-1"
            >
              {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>

          {/* 词汇映射 - 可折叠 */}
          {isExpanded && data.mapping && data.mapping.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
              {(() => {
                const groupedByCategory = data.mapping.reduce((acc, item) => {
                  const cat = item.category || 'General'
                  if (!acc[cat]) acc[cat] = []
                  acc[cat].push(item)
                  return acc
                }, {} as Record<string, typeof data.mapping>)

                return (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.values(groupedByCategory).map((items, idx) => {
                      const pairs: Array<{ from: string; to: string }> = []
                      for (let i = 0; i + 1 < items.length; i += 2) {
                        pairs.push({ from: items[i].to, to: items[i + 1].to })
                      }

                      return pairs.map((pair, pairIdx) => (
                        <div key={`${idx}-${pairIdx}`} className="flex items-center gap-2 text-sm bg-slate-50 dark:bg-slate-900/50 p-2 rounded border border-slate-200 dark:border-slate-700">
                          <span className="text-slate-500 dark:text-slate-400">{pair.from}</span>
                          <ArrowRight size={12} className="text-slate-300 dark:text-slate-600 flex-shrink-0" />
                          <span className="font-semibold text-indigo-600 dark:text-indigo-400">{pair.to}</span>
                        </div>
                      ))
                    })}
                  </div>
                )
              })()}
            </div>
          )}
        </div>

        {/* Your Practice */}
        <div className="p-6 bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <PenTool size={14} className="text-emerald-500" />
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Your Practice</span>
            </div>
            {onDelete && (
              <button
                onClick={onDelete}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={14} />
                <span>删除练习</span>
              </button>
            )}
          </div>
          <div className="space-y-3">
            {userInputs.map((input, idx) => (
              <div key={idx} className="relative group/input animate-in fade-in slide-in-from-bottom-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => handleInputChange(idx, e.target.value)}
                  placeholder="在此输入你的模仿句子..."
                  className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg pl-4 pr-24 py-3 text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition-all placeholder:text-slate-400"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-focus-within/input:opacity-100 transition-opacity">
                  {userInputs.length > 1 && (
                    <button
                      onClick={() => {
                        const newInputs = userInputs.filter((_, i) => i !== idx)
                        onChange(newInputs)
                      }}
                      className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                      title="删除此条"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
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
      </div>
    </div>
  )
}

const LearningSessionPage = ({ onBack }: LearningSessionPageProps) => {
  const { chunks, tedTitle, tedSpeaker, taskId } = useLearning()
  const queryClient = useQueryClient()
  const [isComplete, setIsComplete] = useState(false)
  const [userPractices, setUserPractices] = useState<Record<number, string[]>>({})
  const [isLoading, setIsLoading] = useState(true)

  const [wordPopup, setWordPopup] = useState<{ word: string; x: number; y: number } | null>(null)

  const handleWordClick = (word: string, x: number, y: number) => {
    setWordPopup({ word, x, y })
  }

  const handleComplete = async () => {
    practiceSync.stop()

    if (taskId && Object.keys(userPractices).length > 0) {
      const practiceData = Object.entries(userPractices).map(([index, inputs]) => ({
        index: parseInt(index),
        inputs,
      }))
      try {
        await saveUserPractice(taskId, practiceData)
        toast.success('练习已保存')
      } catch (e) {
        toast.error('保存失败')
      }
    }

    if (taskId) {
      practiceStorage.delete(taskId)
      await updateHistoryStatus(taskId, 'completed')
      queryClient.invalidateQueries({ queryKey: ['history'] })
      console.log('[LearningSessionPage] 更新状态为 completed')
    }

    setIsComplete(true)
  }

  const handleDeletePractice = useCallback((index: number) => {
    const newData = { ...userPractices }
    delete newData[index]
    setUserPractices(newData)
    practiceSync.updateData(newData)
  }, [userPractices])

  const handlePracticeChange = useCallback((index: number, inputs: string[]) => {
    const newData = { ...userPractices, [index]: inputs }
    setUserPractices(newData)
    practiceSync.updateData(newData)
  }, [userPractices])

  useEffect(() => {
    if (!taskId) {
      setIsLoading(false)
      return
    }

    let initialData: Record<number, string[]> = {}

    const localData = practiceStorage.load(taskId)
    if (localData && Object.keys(localData).length > 0) {
      initialData = localData
      setUserPractices(localData)
      setIsLoading(false)
    } else {
      getUserPractice(taskId).then(practice => {
        const practiceMap: Record<number, string[]> = {}
        if (practice && Array.isArray(practice)) {
          practice.forEach((p: { index: number; inputs: string[] }) => {
            practiceMap[p.index] = p.inputs
          })
        }
        setUserPractices(practiceMap)
        setIsLoading(false)
      }).catch(() => {
        setIsLoading(false)
      })
    }

    practiceSync.start(taskId, initialData)

    return () => {
      practiceSync.stop()
    }
  }, [taskId])

  const [learningItems, setLearningItems] = useState<LearningItem[]>([])
  const [parseErrors, setParseErrors] = useState<string[]>([])
  const [debugInfo, setDebugInfo] = useState<string>("")

  useEffect(() => {
    setIsLoading(true)
    console.log("[LearningSessionPage] 收到 chunks:", chunks.length)

    const items: LearningItem[] = []
    const errors: string[] = []

    chunks.forEach((chunk, index) => {
      try {
        const parsed = typeof chunk === 'string' ? dJSON.parse(chunk) : chunk
        console.log(`[LearningSessionPage] 解析练习 ${index + 1} 成功`)
        const mapping = Array.isArray(parsed.mapping)
          ? parsed.mapping
          : Object.entries(parsed.map || {}).flatMap(([from, toList]) =>
              Array.isArray(toList) ? toList.map((to: string) => ({ from, to })) : []
            )

        items.push({
          id: index,
          original: parsed.original || parsed.original_paragraph || '',
          mimic: parsed.imitation || parsed.mimic || '',
          mapping,
        })
      } catch (error) {
        errors.push(`练习 ${index + 1}: ${(error as Error).message}`)
        console.error(`[LearningSessionPage] 解析练习 ${index + 1} 失败:`, error)
      }
    })

    console.log("[LearningSessionPage] 最终 items:", items.length, "errors:", errors.length)
    setDebugInfo(`items: ${items.length}, errors: ${errors.length}`)
    setLearningItems(items)
    setParseErrors(errors)
    setIsLoading(false)
  }, [chunks])

  if (isComplete) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
            练习完成！
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            你已完成本次学习
          </p>
          <button
            onClick={onBack}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            返回任务列表
          </button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={40} className="animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-slate-600 dark:text-slate-400">加载中...</p>
        </div>
      </div>
    )
  }

  if (learningItems.length === 0) {
    if (parseErrors.length > 0 || debugInfo === "items: 0, errors: 0") {
      return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="text-6xl mb-4">🔍</div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
              暂无学习内容
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mb-4">
              {debugInfo || "请从历史记录选择一个任务"}
            </p>
            {parseErrors.length > 0 && (
              <div className="text-left text-sm text-red-600 mb-4 bg-red-50 dark:bg-red-900/20 p-3 rounded max-h-48 overflow-y-auto">
                {parseErrors.map((err, i) => (
                  <div key={i} className="mb-1">{err}</div>
                ))}
              </div>
            )}
            <div className="text-xs text-slate-500 mb-4 font-mono bg-slate-100 dark:bg-slate-800 p-2 rounded">
              chunks: {chunks.length}
            </div>
            <button
              onClick={onBack}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              返回任务列表
            </button>
          </div>
        </div>
      )
    }
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📚</div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
            暂无学习内容
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mb-4">
            请先选择一个任务开始学习
          </p>
          <button
            onClick={onBack}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            返回任务列表
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 pb-32">
      {/* 顶部导航 */}
      <div className="sticky top-0 z-10 bg-white/90 dark:bg-slate-950/90 backdrop-blur-md py-4 mb-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-white transition-colors"
        >
          <ArrowRight className="rotate-180" size={20} />
          <span className="hidden sm:inline">返回任务列表</span>
        </button>
        <div className="text-center">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">
            {tedTitle || 'TED Learning'}
          </h2>
          <p className="text-xs text-slate-500">{tedSpeaker || 'Unknown Speaker'}</p>
        </div>
        <button className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200">
          <MoreHorizontal size={24} />
        </button>
      </div>

      {/* 练习卡片列表 */}
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-500">
        {learningItems.map((item, index) => (
          <LearningCard
            key={item.id || index}
            data={item}
            index={index}
            userInputs={userPractices[index] || ['']}
            onChange={(inputs) => handlePracticeChange(index, inputs)}
            onDelete={() => handleDeletePractice(index)}
            onWordClick={handleWordClick}
          />
        ))}

        {/* 完成按钮 */}
        <div className="text-center pt-10 pb-20">
          <button
            onClick={handleComplete}
            className="bg-slate-900 dark:bg-indigo-600 text-white px-8 py-3 rounded-full font-bold shadow-lg hover:shadow-xl transition-all hover:-translate-y-1"
          >
            完成本节练习 🎉
          </button>
        </div>
      </div>

      {/* 单词释义弹窗 */}
      {wordPopup && (
        <WordPopup
          word={wordPopup.word}
          x={wordPopup.x}
          y={wordPopup.y}
          onClose={() => setWordPopup(null)}
        />
      )}
    </div>
  )
}

export default LearningSessionPage
