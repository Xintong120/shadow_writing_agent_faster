// frontend/src/pages/SettingsPage.tsx
// 系统设置页面 - API配置、偏好设置、存储管理

import { useState, useEffect } from 'react'
import { Database, Settings, Cpu, Trash2, Moon, Sun, Globe, Wifi, WifiOff, RefreshCw, Save, Check, HardDrive, Folder, Plus } from 'lucide-react'
import { api } from '@/services/api'
import { useToast } from '@/hooks/useToast'
import { fileStorage } from '@/services/fileStorage'
import type { ModelInfo, ProviderModelsResponse } from '@/types/api'

interface ApiService {
  id: string
  provider: string
  name: string
  model: string
  key: string
  status: 'idle' | 'checking' | 'success' | 'error'
  models?: ModelInfo[]
  modelsLoading?: boolean
}

interface GroqApiKey {
  id: string
  key: string
  status: 'idle' | 'checking' | 'success' | 'error'
}

interface SettingsPageProps {
  isDarkMode: boolean
  toggleTheme: () => void
}

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'groq', label: 'GROQ' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'tavily', label: 'Tavily Search' }
]

const SettingsPage = ({ isDarkMode, toggleTheme }: SettingsPageProps) => {
  const { toast } = useToast()
  const [isSaving, setIsSaving] = useState(false)
  const [storageInfo, setStorageInfo] = useState({
    localStorageSize: 0,
    appDataSize: 0,
    totalSize: 0,
    loading: true
  })
  const [apiServices, setApiServices] = useState<ApiService[]>([])
  const [apiRotationEnabled, setApiRotationEnabled] = useState(false)

  // 向后兼容：旧的状态变量（将在迁移完成后移除）
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [groqApiKeys, setGroqApiKeys] = useState<any[]>([])

  // 获取指定服务的模型列表
  const fetchModelsForService = async (serviceId: string) => {
    const service = apiServices.find(s => s.id === serviceId)
    if (!service || !service.key.trim()) return

    const newServices = apiServices.map(s =>
      s.id === serviceId ? { ...s, modelsLoading: true } : s
    )
    setApiServices(newServices)

    try {
      const response = await api.getProviderModels(service.provider, service.key.trim()) as ProviderModelsResponse

      if (response.success && response.data) {
        const updatedServices = newServices.map(s =>
          s.id === serviceId ? {
            ...s,
            models: response.data.models,
            modelsLoading: false
          } : s
        )
        setApiServices(updatedServices)
      } else {
        console.error('Failed to fetch models:', response.message)
        const updatedServices = newServices.map(s =>
          s.id === serviceId ? { ...s, modelsLoading: false } : s
        )
        setApiServices(updatedServices)
      }
    } catch (error) {
      console.error('Error fetching models:', error)
      const updatedServices = newServices.map(s =>
        s.id === serviceId ? { ...s, modelsLoading: false } : s
      )
      setApiServices(updatedServices)
    }
  }

  // 格式化文件大小
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 从旧格式迁移到新格式的辅助函数
  const migrateToNewFormat = (data: any): ApiService[] => {
    const services: ApiService[] = []

    // 迁移Tavily
    if (data.tavily_api_key) {
      services.push({
        id: 'tavily-0',
        provider: 'tavily',
        name: PROVIDER_OPTIONS.find(p => p.value === 'tavily')?.label || 'Tavily',
        key: data.tavily_api_key,
        model: 'search',
        status: 'idle' as const
      })
    }

    // 迁移OpenAI
    if (data.openai_api_key) {
      services.push({
        id: 'openai-0',
        provider: 'openai',
        name: PROVIDER_OPTIONS.find(p => p.value === 'openai')?.label || 'OpenAI',
        key: data.openai_api_key,
        model: 'gpt-4',
        status: 'idle' as const
      })
    }

    // 迁移DeepSeek
    if (data.deepseek_api_key) {
      services.push({
        id: 'deepseek-0',
        provider: 'deepseek',
        name: PROVIDER_OPTIONS.find(p => p.value === 'deepseek')?.label || 'DeepSeek',
        key: data.deepseek_api_key,
        model: 'deepseek-chat',
        status: 'idle' as const
      })
    }

    // 迁移GROQ keys
    const groqKeys = data.groq_api_keys || []
    if (groqKeys.length > 0) {
      groqKeys.forEach((key: string, index: number) => {
        if (key.trim()) {
          services.push({
            id: `groq-${index}`,
            provider: 'groq',
            name: `${PROVIDER_OPTIONS.find(p => p.value === 'groq')?.label || 'GROQ'} ${index + 1}`,
            key: key,
            model: 'llama-3.3-70b-versatile',
            status: 'idle' as const
          })
        }
      })
    } else if (data.groq_api_key) {
      // 向后兼容单个GROQ key
      services.push({
        id: 'groq-0',
        provider: 'groq',
        name: PROVIDER_OPTIONS.find(p => p.value === 'groq')?.label || 'GROQ',
        key: data.groq_api_key,
        model: 'llama-3.3-70b-versatile',
        status: 'idle' as const
      })
    }

    return services
  }

  // 加载设置和存储信息
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await api.getSettings()
        if (settings && typeof settings === 'object' && 'data' in settings) {
          const data = (settings as any).data

          // 迁移到新的ApiService格式
          const migratedServices = migrateToNewFormat(data)
          setApiServices(migratedServices)

          // 同时设置旧的状态变量以保持向后兼容
          setApiKeys([
            { service: 'Tavily Search API', key: data.tavily_api_key || '', status: 'idle' },
            { service: 'OpenAI GPT-4', key: data.openai_api_key || '', status: 'idle' },
            { service: 'DeepSeek API', key: data.deepseek_api_key || '', status: 'idle' }
          ])

          const groqKeys = data.groq_api_keys || []
          if (groqKeys.length > 0) {
            setGroqApiKeys(groqKeys.map((key: string, index: number) => ({
              id: `groq-${index}`,
              key: key,
              status: 'idle' as const
            })))
          } else if (data.groq_api_key) {
            setGroqApiKeys([{
              id: 'groq-0',
              key: data.groq_api_key,
              status: 'idle'
            }])
          }

          // 设置API轮换
          setApiRotationEnabled(data.api_rotation_enabled || false)
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
        // 如果加载失败，尝试从localStorage读取
        const savedKeys = localStorage.getItem('api_keys')
        if (savedKeys) {
          try {
            const parsed = JSON.parse(savedKeys)
            setApiKeys(parsed)
          } catch (e) {
            console.error('Failed to parse saved API keys:', e)
          }
        }

        const savedGroqKeys = localStorage.getItem('groq_api_keys')
        if (savedGroqKeys) {
          try {
            const parsed = JSON.parse(savedGroqKeys) as GroqApiKey[]
            setGroqApiKeys(parsed)
          } catch (e) {
            console.error('Failed to parse saved GROQ API keys:', e)
          }
        }

        // 如果有localStorage数据，也尝试迁移
        const savedServices = localStorage.getItem('api_services')
        if (savedServices) {
          try {
            const parsed = JSON.parse(savedServices) as any[]
            const typedServices: ApiService[] = parsed.map(s => ({
              ...s,
              status: s.status as 'idle' | 'checking' | 'success' | 'error'
            }))
            setApiServices(typedServices)
          } catch (e) {
            console.error('Failed to parse saved API services:', e)
          }
        }
      }
    }

    const loadStorageInfo = async () => {
      try {
        const info = await fileStorage.getStorageInfo()
        setStorageInfo({
          ...info,
          loading: false
        })
      } catch (error) {
        console.error('Failed to load storage info:', error)
        setStorageInfo(prev => ({ ...prev, loading: false }))
      }
    }

    loadSettings()
    loadStorageInfo()
  }, [])

  // 清理存储
  const clearStorage = async (options: { clearLocalStorage?: boolean; clearAppData?: boolean; clearAll?: boolean } = {}) => {
    const { clearLocalStorage = false, clearAppData = false, clearAll = false } = options

    const confirmMessage = clearAll
      ? '确定要清除所有本地缓存数据吗？此操作不可恢复。'
      : `确定要清除${clearLocalStorage ? '本地存储' : ''}${clearLocalStorage && clearAppData ? '和' : ''}${clearAppData ? '应用数据' : ''}吗？`

    if (!window.confirm(confirmMessage)) return

    try {
      const result = await fileStorage.clearStorage(options)

      if (result.errors.length > 0) {
        toast({
          title: '清理完成，但有错误',
          description: result.errors.join(', '),
          variant: 'destructive'
        })
      } else {
        toast({
          title: '缓存已清除',
          variant: 'default'
        })
      }

      // 重新加载存储信息
      const info = await fileStorage.getStorageInfo()
      setStorageInfo({ ...info, loading: false })
    } catch (error) {
      toast({
        title: '清除缓存失败',
        variant: 'destructive'
      })
    }
  }

  const updateKey = (index: number, value: string) => {
    const newKeys = [...apiKeys]
    newKeys[index].key = value
    newKeys[index].status = 'idle'
    setApiKeys(newKeys)
  }

  const updateGroqKey = (id: string, value: string) => {
    const newKeys = groqApiKeys.map(key =>
      key.id === id ? { ...key, key: value, status: 'idle' as const } : key
    )
    setGroqApiKeys(newKeys)
  }

  const addGroqKey = () => {
    const newId = `groq-${Date.now()}`
    setGroqApiKeys([...groqApiKeys, { id: newId, key: '', status: 'idle' }])
  }

  const removeGroqKey = (id: string) => {
    if (groqApiKeys.length > 1) {
      setGroqApiKeys(groqApiKeys.filter(key => key.id !== id))
    } else {
      toast({
        title: '至少需要保留一个 GROQ API 密钥',
        variant: 'destructive'
      })
    }
  }

  const testGroqConnection = async (id: string) => {
    const groqKey = groqApiKeys.find(key => key.id === id)
    if (!groqKey || !groqKey.key.trim()) {
      toast({
        title: '请输入 GROQ API 密钥',
        variant: 'destructive'
      })
      return
    }

    const newKeys = groqApiKeys.map(key =>
      key.id === id ? { ...key, status: 'checking' as const } : key
    )
    setGroqApiKeys(newKeys)

    try {
      const result = await api.testApiKey('groq', groqKey.key.trim())

      const updatedKeys = newKeys.map(key =>
        key.id === id ? { ...key, status: result.success ? 'success' : 'error' } : key
      )
      setGroqApiKeys(updatedKeys)

      if (result.success) {
        toast({
          title: 'GROQ API 连接成功',
          variant: 'default'
        })
      } else {
        toast({
          title: 'GROQ API 连接失败',
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('GROQ API key test failed:', error)
      const updatedKeys = newKeys.map(key =>
        key.id === id ? { ...key, status: 'error' } : key
      )
      setGroqApiKeys(updatedKeys)
      toast({
        title: 'GROQ API 测试失败',
        variant: 'destructive'
      })
    }
  }

  // 将UI中的服务名称映射到后端provider字符串
  const getProviderFromService = (service: string): string => {
    switch (service) {
      case 'Tavily Search API':
        return 'tavily'
      case 'GROQ API':
        return 'groq'
      case 'OpenAI GPT-4':
        return 'openai'
      case 'DeepSeek API':
        return 'deepseek'
      default:
        return service.toLowerCase().replace(/\s+/g, '')
    }
  }

  const testConnection = async (index: number) => {
    const apiKey = apiKeys[index]
    if (!apiKey.key.trim()) {
      toast({
        title: '请输入API密钥',
        variant: 'destructive'
      })
      return
    }

    const newKeys = [...apiKeys]
    newKeys[index].status = 'checking'
    setApiKeys(newKeys)

    try {
      const provider = getProviderFromService(apiKey.service)
      const result = await api.testApiKey(provider, apiKey.key.trim())

      const updatedKeys = [...newKeys]
      updatedKeys[index].status = result.success ? 'success' : 'error'
      setApiKeys(updatedKeys)

      if (result.success) {
        toast({
          title: `${apiKey.service} 连接成功`,
          variant: 'default'
        })
      } else {
        toast({
          title: `${apiKey.service} 连接失败`,
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('API key test failed:', error)
      const updatedKeys = [...newKeys]
      updatedKeys[index].status = 'error'
      setApiKeys(updatedKeys)
      toast({
        title: `${apiKey.service} 测试失败`,
        variant: 'destructive'
      })
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)
    try {
      // 构建设置对象
      const settings: any = {}

      // 从新的apiServices构建设置
      const groqKeys: string[] = []
      apiServices.forEach(service => {
        if (service.provider === 'groq') {
          if (service.key.trim()) {
            groqKeys.push(service.key)
          }
        } else if (service.provider === 'openai') {
          settings.openai_api_key = service.key
        } else if (service.provider === 'deepseek') {
          settings.deepseek_api_key = service.key
        } else if (service.provider === 'tavily') {
          settings.tavily_api_key = service.key
        }

        // 保存模型配置（扩展设置API以支持）
        if (service.model) {
          settings[`${service.provider}_model`] = service.model
        }
      })

      // 处理GROQ API密钥列表
      if (groqKeys.length > 0) {
        settings.groq_api_keys = groqKeys
      }
      settings.api_rotation_enabled = apiRotationEnabled

      await api.updateSettings(settings)

      // 保存到localStorage作为备份
      localStorage.setItem('api_services', JSON.stringify(apiServices))
      localStorage.setItem('api_keys', JSON.stringify(apiKeys)) // 保持向后兼容
      localStorage.setItem('groq_api_keys', JSON.stringify(groqApiKeys)) // 保持向后兼容

      toast({
        title: '设置保存成功',
        variant: 'default'
      })
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast({
        title: '设置保存失败',
        variant: 'destructive'
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
          <Settings className="text-indigo-600 dark:text-indigo-400" />
          系统设置
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          配置你的学习环境和偏好设置。
        </p>
      </header>

      <div className="space-y-8">
        {/* API Configuration */}
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
           <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2 text-lg">
             <Database size={20} className="text-indigo-500" />
             API 连接配置
           </h3>
           <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
             配置外部服务 API Key 以启用智能搜索和影子写作功能。您的 Key 仅存储在本地浏览器中。
           </p>

           <div className="space-y-4">
             {/* 新的API服务配置 */}
             {apiServices.map((service) => (
               <div key={service.id} className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
                 <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                   {/* Provider选择器 */}
                   <div className="w-full sm:w-auto min-w-[140px]">
                     <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                       Provider
                     </label>
                     <select
                       value={service.provider}
                       onChange={(e) => {
                         const newServices = apiServices.map(s =>
                           s.id === service.id ? { ...s, provider: e.target.value, name: PROVIDER_OPTIONS.find(p => p.value === e.target.value)?.label || e.target.value } : s
                         )
                         setApiServices(newServices)
                       }}
                       className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                     >
                       {PROVIDER_OPTIONS.map(option => (
                         <option key={option.value} value={option.value}>
                           {option.label}
                         </option>
                       ))}
                     </select>
                   </div>

                   {/* API Key输入 */}
                   <div className="flex-1 w-full">
                     <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                       API Key
                     </label>
                     <div className="relative">
                       <input
                         type="password"
                         value={service.key || ""}
                         onChange={(e) => {
                           const newServices = apiServices.map(s =>
                             s.id === service.id ? { ...s, key: e.target.value, status: 'idle' as const, models: undefined } : s
                           )
                           setApiServices(newServices)
                         }}
                         placeholder={service.provider === 'openai' ? "sk-........................" : service.provider === 'groq' ? "gsk-........................" : "API Key"}
                         className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg pl-3 pr-10 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-mono"
                       />
                       <div className="absolute right-3 top-2.5">
                         {service.status === 'success' && <Wifi size={16} className="text-emerald-500" />}
                         {service.status === 'error' && <WifiOff size={16} className="text-red-500" />}
                         {service.status === 'checking' && <RefreshCw size={16} className="text-indigo-500 animate-spin" />}
                       </div>
                     </div>
                   </div>

                   {/* 测试连接按钮 */}
                   <button
                     onClick={async () => {
                       if (!service.key.trim()) {
                         toast({
                           title: '请输入API密钥',
                           variant: 'destructive'
                         })
                         return
                       }

                       const newServices = apiServices.map(s =>
                         s.id === service.id ? { ...s, status: 'checking' as const } : s
                       )
                       setApiServices(newServices)

                       try {
                         const result = await api.testApiKey(service.provider, service.key.trim())

                         const updatedServices = newServices.map(s =>
                           s.id === service.id ? { ...s, status: result.success ? 'success' : 'error' } : s
                         )
                         setApiServices(updatedServices)

                         if (result.success) {
                           toast({
                             title: `${service.name} API 连接成功`,
                             variant: 'default'
                           })
                           // 只对AI模型提供商获取模型列表，搜索服务跳过
                           if (service.provider !== 'tavily') {
                             fetchModelsForService(service.id)
                           }
                         } else {
                           toast({
                             title: `${service.name} API 连接失败`,
                             variant: 'destructive'
                           })
                         }
                       } catch (error) {
                         console.error('API key test failed:', error)
                         const updatedServices = newServices.map(s =>
                           s.id === service.id ? { ...s, status: 'error' } : s
                         )
                         setApiServices(updatedServices)
                         toast({
                           title: `${service.name} API 测试失败`,
                           variant: 'destructive'
                         })
                       }
                     }}
                     disabled={service.status === 'checking'}
                     className={`w-full sm:w-auto px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border ${
                       service.status === 'success'
                         ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                         : service.status === 'error'
                         ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                         : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600'
                     }`}
                   >
                     {service.status === 'checking' ? '连接中...' : service.status === 'success' ? '连接正常' : service.status === 'error' ? '连接失败' : '测试连接'}
                   </button>
                 </div>

                 {/* 模型选择器 - 仅在API连接成功后显示 */}
                 {service.status === 'success' && (
                   <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-600">
                     <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                       <div className="flex-1 w-full">
                         <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                           模型选择
                         </label>
                         <div className="relative">
                           <select
                             value={service.model}
                             onChange={(e) => {
                               const newServices = apiServices.map(s =>
                                 s.id === service.id ? { ...s, model: e.target.value } : s
                               )
                               setApiServices(newServices)
                             }}
                             disabled={service.modelsLoading}
                             className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none disabled:opacity-50"
                           >
                             {service.models?.map(model => (
                               <option key={model.id} value={model.id}>
                                 {model.name} - {model.description}
                               </option>
                             )) || (
                               <option value={service.model}>{service.model}</option>
                             )}
                           </select>
                           {service.modelsLoading && (
                             <div className="absolute right-3 top-2.5">
                               <RefreshCw size={16} className="text-indigo-500 animate-spin" />
                             </div>
                           )}
                         </div>
                       </div>
                     </div>
                   </div>
                 )}
               </div>
             ))}

             {/* 添加新API服务按钮 */}
             <button
               onClick={() => {
                 const newId = `service-${Date.now()}`
                 const defaultProvider = PROVIDER_OPTIONS[0]
                 setApiServices([...apiServices, {
                   id: newId,
                   provider: defaultProvider.value,
                   name: defaultProvider.label,
                   key: '',
                   model: '',
                   status: 'idle' as const
                 }])
               }}
               className="w-full py-3 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-lg text-slate-500 dark:text-slate-400 hover:border-indigo-500 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors text-sm font-medium"
             >
               + 添加 API 服务
             </button>

             {/* 旧的API配置 - 暂时保留以保持向后兼容 */}
             {apiKeys.map((api, idx) => (
               <div key={idx} className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                 <div className="flex-1 w-full">
                   <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                     {api.service}
                   </label>
                   <div className="relative">
                     <input
                       type="password"
                       value={api.key || "sk-........................"}
                       onChange={(e) => updateKey(idx, e.target.value)}
                       className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg pl-3 pr-10 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-mono"
                     />
                     <div className="absolute right-3 top-2.5">
                       {api.status === 'success' && <Wifi size={16} className="text-emerald-500" />}
                       {api.status === 'error' && <WifiOff size={16} className="text-red-500" />}
                       {api.status === 'checking' && <RefreshCw size={16} className="text-indigo-500 animate-spin" />}
                     </div>
                   </div>
                 </div>
                 <button
                   onClick={() => testConnection(idx)}
                   disabled={api.status === 'checking'}
                   className={`w-full sm:w-auto px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border ${
                     api.status === 'success'
                       ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                       : api.status === 'error'
                       ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                       : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600'
                   }`}
                 >
                   {api.status === 'checking' ? '连接中...' : api.status === 'success' ? '连接正常' : api.status === 'error' ? '连接失败' : '测试连接'}
                 </button>
               </div>
             ))}

             {/* GROQ API Keys */}
             {groqApiKeys.map((groqKey, idx) => (
               <div key={groqKey.id} className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                 <div className="flex-1 w-full">
                   <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                     GROQ API #{idx + 1}
                   </label>
                   <div className="relative">
                     <input
                       type="password"
                       value={groqKey.key || "gsk-........................"}
                       onChange={(e) => updateGroqKey(groqKey.id, e.target.value)}
                       className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg pl-3 pr-16 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-mono"
                     />
                     <div className="absolute right-12 top-2.5">
                       {groqKey.status === 'success' && <Wifi size={16} className="text-emerald-500" />}
                       {groqKey.status === 'error' && <WifiOff size={16} className="text-red-500" />}
                       {groqKey.status === 'checking' && <RefreshCw size={16} className="text-indigo-500 animate-spin" />}
                     </div>
                     <button
                       onClick={() => removeGroqKey(groqKey.id)}
                       className="absolute right-3 top-2.5 text-slate-400 hover:text-red-500 transition-colors"
                       disabled={groqApiKeys.length <= 1}
                     >
                       <Trash2 size={14} />
                     </button>
                   </div>
                 </div>
                 <button
                   onClick={() => testGroqConnection(groqKey.id)}
                   disabled={groqKey.status === 'checking'}
                   className={`w-full sm:w-auto px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border ${
                     groqKey.status === 'success'
                       ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                       : groqKey.status === 'error'
                       ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                       : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600'
                   }`}
                 >
                   {groqKey.status === 'checking' ? '连接中...' : groqKey.status === 'success' ? '连接正常' : groqKey.status === 'error' ? '连接失败' : '测试连接'}
                 </button>
               </div>
             ))}

             <div className="flex items-center justify-between">
               <div className="flex items-center gap-3">
                 <label className="flex items-center gap-2 text-sm">
                   <input
                     type="checkbox"
                     checked={apiRotationEnabled}
                     onChange={(e) => setApiRotationEnabled(e.target.checked)}
                     className="rounded border-slate-300 dark:border-slate-600"
                   />
                   <span className="text-slate-700 dark:text-slate-300">启用 GROQ API 轮换</span>
                 </label>
               </div>
               <button
                 onClick={addGroqKey}
                 className="text-sm text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1"
               >
                 + 添加 GROQ API 密钥
               </button>
             </div>
           </div>
        </section>

        {/* Preferences */}
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
           <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2 text-lg">
             <Settings size={20} className="text-indigo-500" />
             偏好设置
           </h3>
           <div className="space-y-5">
             <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-indigo-900/30 text-indigo-400' : 'bg-orange-100 text-orange-500'}`}>
                    {isDarkMode ? <Moon size={20} /> : <Sun size={20} />}
                  </div>
                  <div>
                    <span className="text-slate-900 dark:text-white font-medium block">界面外观</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">切换深色/浅色模式</span>
                  </div>
                </div>
                <button
                  onClick={toggleTheme}
                  className={`w-14 h-7 rounded-full p-1 transition-colors duration-300 relative ${isDarkMode ? 'bg-indigo-600' : 'bg-slate-200'}`}
                  aria-label="Toggle Dark Mode"
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow-sm transform transition-transform duration-300 ${isDarkMode ? 'translate-x-7' : 'translate-x-0'}`}></div>
                </button>
             </div>

             <hr className="border-slate-100 dark:border-slate-700" />

             <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-500">
                    <Globe size={20} />
                  </div>
                  <div>
                    <span className="text-slate-900 dark:text-white font-medium block">界面语言</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">选择应用显示语言</span>
                  </div>
                </div>
                <select className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm px-3 py-1.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-indigo-500/20">
                  <option>简体中文</option>
                  <option>English</option>
                  <option>日本語</option>
                </select>
             </div>
           </div>
        </section>

        {/* Cache */}
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
           <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2 text-lg">
             <Cpu size={20} className="text-indigo-500" />
             存储管理
           </h3>
           <div className="space-y-4">
             <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-700">
               <div>
                 <p className="text-slate-700 dark:text-slate-200 font-medium">本地缓存数据</p>
                 <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                   已使用 {storageInfo.loading ? '计算中...' : formatBytes(storageInfo.totalSize)} (包含设置和学习数据)
                 </p>
               </div>
               <button
                 onClick={() => clearStorage({ clearAll: true })}
                 className="flex items-center gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 px-4 py-2 rounded-lg transition-colors text-sm font-medium"
               >
                 <Trash2 size={16} /> 清除缓存
               </button>
             </div>

             <div className="grid grid-cols-2 gap-4 text-sm">
               <div className="text-slate-500 dark:text-slate-400">
                 <span className="flex items-center gap-1">
                   <Database size={14} />
                   本地存储: {storageInfo.loading ? '...' : formatBytes(storageInfo.localStorageSize)}
                 </span>
               </div>
               <div className="text-slate-500 dark:text-slate-400">
                 <span className="flex items-center gap-1">
                   <Folder size={14} />
                   应用数据: {storageInfo.loading ? '...' : formatBytes(storageInfo.appDataSize)}
                 </span>
               </div>
             </div>
           </div>
        </section>
      </div>
    </div>
  )
}

export default SettingsPage
