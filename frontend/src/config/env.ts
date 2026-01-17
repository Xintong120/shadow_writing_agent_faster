// 环境变量配置 - 可被 Jest mock
export const config = {
  API_BASE: 'http://localhost:8000',
  IS_DEBUG: false,
}

// 在浏览器环境中使用 Vite 的环境变量
if (typeof window !== 'undefined') {
  try {
    // @ts-ignore
    const env = import.meta.env
    if (env) {
      config.API_BASE = env.VITE_API_BASE_URL || config.API_BASE
      config.IS_DEBUG = env.VITE_ENABLE_DEBUG === 'true'
    }
  } catch {
    // 在 Jest 环境中忽略
  }
}
