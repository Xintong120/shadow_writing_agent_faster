import { useState, useEffect, useRef, useMemo } from 'react'
import { Database, Settings, Cpu, Trash2, Moon, Sun, Globe, Wifi, WifiOff, RefreshCw, Save, Check, Folder, Plus, ChevronDown, Trash, Search, X } from 'lucide-react'
import { api } from '@/services/api'
import { useToast } from '@/hooks/useToast'
import { fileStorage } from '@/services/fileStorage'
import type { ModelInfo, ProviderModelsResponse } from '@/types/api'
import type { ProviderOption } from '@/services/api'

interface SelectOption {
  value: string
  label: string
}

const Select = ({
  options,
  value,
  onChange,
  label,
  placeholder = '搜索...',
  emptyMessage = '未找到匹配的选项',
  disabled = false
}: {
  options: SelectOption[]
  value: string
  onChange: (value: string) => void
  label: string
  placeholder?: string
  emptyMessage?: string
  disabled?: boolean
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredOptions = useMemo(() => {
    if (!search) return options
    const s = search.toLowerCase()
    return options.filter(o =>
      o.label.toLowerCase().includes(s) ||
      o.value.toLowerCase().includes(s)
    )
  }, [options, search])

  const selectedOption = options.find(o => o.value === value)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
        {label}
      </label>
      <button
        type="button"
        onClick={() => {
          if (disabled) return
          setIsOpen(!isOpen)
          if (!isOpen) {
            setSearch('')
            setTimeout(() => inputRef.current?.focus(), 0)
          }
        }}
        disabled={disabled}
        className={`w-full h-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-left flex items-center justify-between transition-colors ${
          disabled
            ? 'opacity-50 cursor-not-allowed'
            : 'text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none cursor-pointer hover:border-indigo-400'
        }`}
      >
        <span className="truncate">{selectedOption?.label || value || '请选择...'}</span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden">
          <div className="p-2 border-b border-slate-200 dark:border-slate-700">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-400" />
              <input
                ref={inputRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={placeholder}
                className="w-full h-8 bg-slate-100 dark:bg-slate-800 border-0 rounded-md pl-9 pr-8 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2 top-2 p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                >
                  <X className="w-3.5 h-3.5 text-slate-400" />
                </button>
              )}
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">{emptyMessage}</div>
            ) : (
              filteredOptions.map(option => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    onChange(option.value)
                    setIsOpen(false)
                    setSearch('')
                  }}
                  className={`w-full px-3 py-2 text-left text-sm transition-colors ${
                    option.value === value
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {option.label}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface ApiKeyItem {
  id: string
  key: string
  status: 'idle' | 'checking' | 'success' | 'error'
}

interface SettingsPageProps {
  isDarkMode: boolean
  toggleTheme: () => void
}

const SettingsPage = ({ isDarkMode, toggleTheme }: SettingsPageProps) => {
  const { toast } = useToast()
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [storageInfo, setStorageInfo] = useState({
    localStorageSize: 0,
    appDataSize: 0,
    totalSize: 0,
    loading: true
  })

  const [providerOptions, setProviderOptions] = useState<ProviderOption[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string>('groq')
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [modelsLoading, setModelsLoading] = useState(false)
  const [apiRotationEnabled, setApiRotationEnabled] = useState(false)
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [tavilyStatus, setTavilyStatus] = useState<'idle' | 'checking' | 'success' | 'error'>('idle')

  const [tavilyKey, setTavilyKey] = useState('')
  const [tavilyEnabled, setTavilyEnabled] = useState(false)

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  useEffect(() => {
    let mounted = true

    const loadSettings = async () => {
      if (!mounted) return
      setIsLoading(true)

      try {
        console.log('[SettingsPage] 1. 获取 Provider 列表...')
        const providers = await api.getProviderOptions()
        console.log('[SettingsPage] Provider 列表:', providers)
        if (mounted && providers.length > 0) {
          setProviderOptions(providers)
          setSelectedProvider(providers[0].value)
        }

        console.log('[SettingsPage] 2. 获取设置...')
        const settings = await api.getSettings() as { data?: any }
        console.log('[SettingsPage] 设置:', settings)
        if (mounted && settings.data) {
          const data = settings.data
          if (data.api_keys && Array.isArray(data.api_keys) && data.api_keys.length > 0) {
            setApiKeys(data.api_keys.map((key: string, idx: number) => ({
              id: `key-${idx}`,
              key,
              status: 'idle' as const
            })))
          }
          if (data.current_api_provider) {
            setSelectedProvider(data.current_api_provider)
          }
          if (data.model_name) {
            setSelectedModel(data.model_name)
          }
          setApiRotationEnabled(data.api_rotation_enabled || false)
        }

        console.log('[SettingsPage] 3. 获取 Tavily 配置...')
        const tavily = await api.getTavilyConfig()
        console.log('[SettingsPage] Tavily:', tavily)
        if (mounted) {
          setTavilyKey(tavily.api_key || '')
          setTavilyEnabled(tavily.enabled || false)
        }

        console.log('[SettingsPage] 4. 完成加载')
        console.log('[SettingsPage] providerOptions:', providerOptions.length, '项')
      } catch (error) {
        console.error('[SettingsPage] 加载失败:', error)
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }

    const loadStorageInfo = async () => {
      try {
        const info = await fileStorage.getStorageInfo()
        if (mounted) {
          setStorageInfo({ ...info, loading: false })
        }
      } catch (error) {
        console.error('[SettingsPage] 加载存储信息失败:', error)
        if (mounted) {
          setStorageInfo(prev => ({ ...prev, loading: false }))
        }
      }
    }

    loadSettings()
    loadStorageInfo()

    return () => {
      mounted = false
    }
  }, [])

  const [fetchError, setFetchError] = useState<string | null>(null)

  const fetchModels = async () => {
    if (!selectedProvider || apiKeys.length === 0) return

    const firstKey = apiKeys.find(k => k.key.trim())
    if (!firstKey?.key.trim()) return

    setModelsLoading(true)
    setFetchError(null)

    try {
      const response = await api.getProviderModels(selectedProvider, firstKey.key.trim()) as ProviderModelsResponse
      if (response.success && response.data?.models) {
        setAvailableModels(response.data.models)
      } else if (!response.success && response.message) {
        setFetchError(response.message)
        setAvailableModels([])
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
      setFetchError(error instanceof Error ? error.message : '获取模型列表失败')
      setAvailableModels([])
    } finally {
      setModelsLoading(false)
    }
  }

  const testConnection = async (keyId: string) => {
    const keyItem = apiKeys.find(k => k.id === keyId)
    if (!keyItem || !keyItem.key.trim()) {
      toast({ title: '请输入 API Key', variant: 'destructive' })
      return
    }

    setApiKeys(prev => prev.map(k => k.id === keyId ? { ...k, status: 'checking' as const } : k))

    try {
      const result = await api.testApiKey(selectedProvider, keyItem.key.trim())
      setApiKeys(prev => prev.map(k => k.id === keyId ? { ...k, status: result.success ? 'success' as const : 'error' as const } : k))

      if (result.success) {
        toast({ title: 'API 连接成功', variant: 'default' })
        fetchModels()
      } else {
        toast({ title: result.message || 'API 连接失败', variant: 'destructive' })
      }
    } catch (error) {
      setApiKeys(prev => prev.map(k => k.id === keyId ? { ...k, status: 'error' as const } : k))
      toast({ title: 'API 连接测试失败', variant: 'destructive' })
    }
  }

  const testTavilyConnection = async () => {
    if (!tavilyKey.trim()) {
      toast({ title: '请输入 Tavily API Key', variant: 'destructive' })
      return
    }

    setTavilyStatus('checking')

    try {
      const result = await api.testApiKey('tavily', tavilyKey.trim())
      setTavilyStatus(result.success ? 'success' : 'error')

      if (result.success) {
        toast({ title: 'Tavily API 连接成功', variant: 'default' })
      } else {
        toast({ title: result.message || 'Tavily API 连接失败', variant: 'destructive' })
      }
    } catch (error) {
      setTavilyStatus('error')
      toast({ title: 'Tavily API 连接测试失败', variant: 'destructive' })
    }
  }

  const addApiKey = () => {
    const newId = `key-${Date.now()}`
    setApiKeys(prev => [...prev, { id: newId, key: '', status: 'idle' as const }])
  }

  const removeApiKey = (keyId: string) => {
    if (apiKeys.length > 1) {
      setApiKeys(prev => prev.filter(k => k.id !== keyId))
    } else {
      toast({ title: '至少需要保留一个 API Key', variant: 'destructive' })
    }
  }

  const updateApiKey = (keyId: string, value: string) => {
    setApiKeys(prev => prev.map(k => k.id === keyId ? { ...k, key: value, status: 'idle' as const } : k))
  }

  const clearStorage = async (options: { clearAll?: boolean } = {}) => {
    const confirmMessage = options.clearAll
      ? '确定要清除所有本地缓存数据吗？此操作不可恢复。'
      : '确定要清除缓存数据吗？'

    if (!window.confirm(confirmMessage)) return

    try {
      const result = await fileStorage.clearStorage(options)
      if (result.errors.length > 0) {
        toast({ title: '清理完成，但有错误', description: result.errors.join(', '), variant: 'destructive' })
      } else {
        toast({ title: '缓存已清除', variant: 'default' })
      }

      const info = await fileStorage.getStorageInfo()
      setStorageInfo({ ...info, loading: false })
    } catch (error) {
      toast({ title: '清除缓存失败', variant: 'destructive' })
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)

    try {
      const validKeys = apiKeys.filter(k => k.key.trim()).map(k => k.key.trim())

      if (validKeys.length === 0) {
        toast({ title: '请至少输入一个 API Key', variant: 'destructive' })
        setIsSaving(false)
        return
      }

      await api.saveApiConfig({
        provider: selectedProvider,
        api_keys: validKeys,
        model: selectedModel,
        rotation_enabled: apiRotationEnabled
      })

      await api.updateTavilyConfig({
        api_key: tavilyKey,
        enabled: tavilyEnabled
      })

      localStorage.removeItem('pending_api_config')

      toast({ title: '设置保存成功', variant: 'default' })

      const info = await fileStorage.getStorageInfo()
      setStorageInfo({ ...info, loading: false })
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast({ title: '设置保存失败', variant: 'destructive' })
    } finally {
      setIsSaving(false)
    }
  }

  const currentProviderLabel = providerOptions.find(p => p.value === selectedProvider)?.label || selectedProvider

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 animate-in fade-in slide-in-from-bottom-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
          <Settings className="text-indigo-600 dark:text-indigo-400" />
          系统设置
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          配置外部服务 API Key 以启用智能搜索和影子写作功能。
        </p>
      </header>

      <div className="space-y-8">
        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2 text-lg">
            <Database size={20} className="text-indigo-500" />
            LLM Provider 配置
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            选择 Provider 并配置 API Keys。多个 Key 可用于自动轮换。
          </p>

          <div className="space-y-6">
            <Select
              label="Provider"
              options={providerOptions}
              value={selectedProvider}
              onChange={(value) => {
                setSelectedProvider(value)
                setSelectedModel('')
                setAvailableModels([])
                setApiKeys([{ id: 'key-default', key: '', status: 'idle' as const }])
              }}
              placeholder="搜索 Provider..."
              emptyMessage="未找到匹配的 Provider"
            />

            <div className="space-y-3">
              <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                API Keys
              </label>

              {apiKeys.map((keyItem) => (
                <div key={keyItem.id} className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                  <div className="flex-1 w-full">
                    <input
                      type="password"
                      value={keyItem.key}
                      onChange={(e) => updateApiKey(keyItem.id, e.target.value)}
                      placeholder={`${currentProviderLabel} API Key`}
                      className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none font-mono"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => testConnection(keyItem.id)}
                      disabled={keyItem.status === 'checking'}
                      className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border flex items-center gap-2 ${
                        keyItem.status === 'success'
                          ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                          : keyItem.status === 'error'
                          ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                          : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600'
                      }`}
                    >
                      {keyItem.status === 'checking' ? (
                        <RefreshCw size={16} className="animate-spin" />
                      ) : keyItem.status === 'success' ? (
                        <Check size={16} />
                      ) : keyItem.status === 'error' ? (
                        <WifiOff size={16} />
                      ) : (
                        <Wifi size={16} />
                      )}
                      {keyItem.status === 'checking' ? '连接中...' : keyItem.status === 'success' ? '连接成功' : keyItem.status === 'error' ? '连接失败' : '测试连接'}
                    </button>
                    <button
                      onClick={() => removeApiKey(keyItem.id)}
                      disabled={apiKeys.length <= 1}
                      className="p-2.5 text-slate-400 hover:text-red-500 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Trash size={16} />
                    </button>
                  </div>
                </div>
              ))}

              <button
                onClick={addApiKey}
                className="text-sm text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1"
              >
                <Plus size={16} />
                添加 API Key
              </button>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={apiRotationEnabled}
                  onChange={(e) => setApiRotationEnabled(e.target.checked)}
                  className="rounded border-slate-300 dark:border-slate-600"
                />
                <span className="text-slate-700 dark:text-slate-300">启用 API Key 轮换</span>
              </label>
            </div>

            {apiKeys.some(k => k.status === 'success') && (
              <Select
                label="模型选择"
                options={availableModels.map(m => ({ value: m.id, label: m.name }))}
                value={selectedModel}
                onChange={(value) => setSelectedModel(value)}
                placeholder="搜索模型..."
                emptyMessage={fetchError || '无可用模型'}
                disabled={modelsLoading}
              />
            )}
          </div>
        </section>

        <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2 text-lg">
            <Globe size={20} className="text-indigo-500" />
            Tavily 搜索配置
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Tavily 是专用搜索引擎，API Key 独立存储。
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                Tavily API Key
              </label>
              <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                <div className="flex-1 w-full">
                  <input
                    type="password"
                    value={tavilyKey}
                    onChange={(e) => {
                      setTavilyKey(e.target.value)
                      if (tavilyStatus !== 'idle') setTavilyStatus('idle')
                    }}
                    placeholder="Tavily API Key"
                    className={`w-full rounded-lg px-3 py-2.5 text-sm font-mono transition-colors ${
                      tavilyStatus === 'success'
                        ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
                        : tavilyStatus === 'error'
                        ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none'
                    }`}
                  />
                </div>
                <button
                  onClick={testTavilyConnection}
                  disabled={tavilyStatus === 'checking'}
                  className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border flex items-center gap-2 ${
                    tavilyStatus === 'success'
                      ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                      : tavilyStatus === 'error'
                      ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                      : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600'
                  }`}
                >
                  {tavilyStatus === 'checking' ? (
                    <RefreshCw size={16} className="animate-spin" />
                  ) : tavilyStatus === 'success' ? (
                    <Check size={16} />
                  ) : tavilyStatus === 'error' ? (
                    <WifiOff size={16} />
                  ) : (
                    <Wifi size={16} />
                  )}
                  {tavilyStatus === 'checking' ? '连接中...' : tavilyStatus === 'success' ? '连接成功' : tavilyStatus === 'error' ? '连接失败' : '测试连接'}
                </button>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={tavilyEnabled}
                onChange={(e) => setTavilyEnabled(e.target.checked)}
                className="rounded border-slate-300 dark:border-slate-600"
              />
              <span className="text-slate-700 dark:text-slate-300">启用 Tavily 搜索</span>
            </label>
          </div>
        </section>

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
                <Trash2 size={16} />
                清除缓存
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

        <section className="flex justify-end">
          <button
            onClick={saveSettings}
            disabled={isSaving || isLoading}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {isSaving ? (
              <>
                <RefreshCw size={18} className="animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save size={18} />
                保存配置
              </>
            )}
          </button>
        </section>
      </div>
    </div>
  )
}

export default SettingsPage
