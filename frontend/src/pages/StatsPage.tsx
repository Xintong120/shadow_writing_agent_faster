// frontend/src/pages/StatsPage.tsx
// 数据统计页面 - 学习数据分析和可视化

import { useState, useEffect } from 'react';
import { BarChart2, Clock, PenTool, Library, Calendar, Target, Edit2, Check, X, Sparkles } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  getLocalStats,
  generateHeatmapData,
  getLearningGoals,
  saveLearningGoals,
  updateGoal,
  getCurrentGoalProgress,
  type LocalStats,
  type HeatmapData,
  type LearningGoals
} from '@/services/localStats'

const StatsPage = () => {
  const { authStatus } = useAuth()

  // --- 状态管理 ---
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth()); // 0-11
  const [goalPeriod, setGoalPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [isEditingGoal, setIsEditingGoal] = useState(false);

  // --- 数据状态 ---
  const [stats, setStats] = useState<LocalStats>({
    totalLearningTime: 0,
    totalSentences: 0,
    totalTedTalks: 0
  });
  const [heatmapData, setHeatmapData] = useState<HeatmapData[]>([]);
  const [goals, setGoals] = useState<LearningGoals>({
    daily: { target: 20, current: 0, unit: '句' },
    weekly: { target: 140, current: 0, unit: '句' },
    monthly: { target: 600, current: 0, unit: '句' }
  });

  // --- UI状态 ---
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tempGoalTarget, setTempGoalTarget] = useState(0);

  // 获取用户ID（与HistoryPage保持一致）
  const getUserId = () => authStatus === 'guest' ? 'guest_user' : 'user_123';

  // 加载数据函数
  const loadStatsData = async () => {
    try {
      setLoading(true);
      setError(null);

      const userId = getUserId();

      // 加载统计数据
      const statsData = await getLocalStats(userId);
      setStats(statsData);

      // 加载热力图数据
      const heatmap = await generateHeatmapData(userId, currentYear, currentMonth);
      setHeatmapData(heatmap);

      // 加载学习目标
      const goalsData = getLearningGoals(userId);
      setGoals(goalsData);

      // 计算当前目标进度
      const currentProgress = await getCurrentGoalProgress(userId, goalPeriod);
      setGoals(prev => ({
        ...prev,
        [goalPeriod]: { ...prev[goalPeriod], current: currentProgress }
      }));

    } catch (err) {
      console.error('加载统计数据失败:', err);
      setError('加载数据失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // --- 辅助函数 ---

  // 计算月份第一天是星期几，用于 Grid 对齐
  const getFirstDayOffset = (year: number, month: number) => {
    return new Date(year, month, 1).getDay(); // 0 (Sun) - 6 (Sat)
  };

  // 根据句子数量返回热力图颜色等级
  const getIntensityColor = (count: number) => {
    if (count === 0) return 'bg-slate-100 dark:bg-slate-800';
    if (count < 5) return 'bg-indigo-200 dark:bg-indigo-900/40';
    if (count < 15) return 'bg-indigo-400 dark:bg-indigo-700/60';
    if (count < 25) return 'bg-indigo-500 dark:bg-indigo-600';
    return 'bg-indigo-600 dark:bg-indigo-500 shadow-sm shadow-indigo-500/50';
  };

  // 保存目标设置
  const handleSaveGoal = () => {
    const userId = getUserId();
    const newTarget = parseInt(tempGoalTarget.toString()) || 0;

    // 更新本地存储
    updateGoal(userId, goalPeriod, newTarget);

    // 更新本地状态
    setGoals(prev => ({
      ...prev,
      [goalPeriod]: { ...prev[goalPeriod], target: newTarget }
    }));

    setIsEditingGoal(false);
  };

  // 加载数据
  useEffect(() => {
    loadStatsData();
  }, [authStatus, currentYear, currentMonth]);

  // 当年月改变时重新加载热力图数据
  useEffect(() => {
    if (authStatus) {
      generateHeatmapData(getUserId(), currentYear, currentMonth).then(setHeatmapData);
    }
  }, [currentYear, currentMonth, authStatus]);

  // 切换目标周期时重置编辑数值
  useEffect(() => {
    setTempGoalTarget(goals[goalPeriod].target);
  }, [goalPeriod, goals]);

  // 计算当前目标进度百分比
  const currentGoal = goals[goalPeriod];
  const progressPercent = Math.min(100, Math.round((currentGoal.current / currentGoal.target) * 100));

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 pb-24 animate-in fade-in slide-in-from-bottom-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
          <BarChart2 className="text-indigo-600 dark:text-indigo-400" />
          数据统计与目标
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          追踪你的影子写作进度，保持学习连贯性。
        </p>
      </header>

      {/* 1. 核心指标概览 (Core Metrics) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {loading ? (
          // 加载状态
          <>
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-5 animate-pulse">
                <div className="w-14 h-14 rounded-full bg-slate-200 dark:bg-slate-700"></div>
                <div className="flex-1">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded mb-2"></div>
                  <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-20"></div>
                </div>
              </div>
            ))}
          </>
        ) : error ? (
          // 错误状态
          <div className="col-span-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6">
            <p className="text-red-600 dark:text-red-400 text-center">{error}</p>
          </div>
        ) : (
          <>
            {/* 总练习时长 */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-5">
               <div className="w-14 h-14 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                 <Clock size={28} />
               </div>
               <div>
                 <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">总练习时长</p>
                 <p className="text-3xl font-bold text-slate-900 dark:text-white">{Math.round(stats.totalLearningTime / 3600 * 10) / 10} <span className="text-sm font-normal text-slate-500">小时</span></p>
               </div>
            </div>

            {/* 模仿句子总数 */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-5">
               <div className="w-14 h-14 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                 <PenTool size={28} />
               </div>
               <div>
                 <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">累计模仿句子</p>
                 <p className="text-3xl font-bold text-slate-900 dark:text-white">{stats.totalSentences.toLocaleString()} <span className="text-sm font-normal text-slate-500">句</span></p>
               </div>
            </div>

            {/* 学习 TED 演讲数 */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-5">
               <div className="w-14 h-14 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                 <Library size={28} />
               </div>
               <div>
                 <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">完成 TED 演讲</p>
                 <p className="text-3xl font-bold text-slate-900 dark:text-white">{stats.totalTedTalks} <span className="text-sm font-normal text-slate-500">个</span></p>
               </div>
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* 2. 日历热力图 (Calendar Heatmap) - 占 2/3 宽度 */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 p-6 sm:p-8 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <div>
               <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                 <Calendar className="text-indigo-500" size={20} />
                 学习热力图
               </h3>
               <p className="text-xs text-slate-500 dark:text-slate-400">统计每日模仿句子数量</p>
            </div>

            {/* 年月选择器 */}
            <div className="flex gap-2">
              <select
                value={currentYear}
                onChange={(e) => setCurrentYear(parseInt(e.target.value))}
                className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm px-3 py-1.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}年</option>)}
              </select>
              <select
                value={currentMonth}
                onChange={(e) => setCurrentMonth(parseInt(e.target.value))}
                className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm px-3 py-1.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {Array.from({length: 12}, (_, i) => (
                  <option key={i} value={i}>{i + 1}月</option>
                ))}
              </select>
            </div>
          </div>

          {/* Grid Layout for Heatmap */}
          <div className="w-full">
            {/* Weekday Headers */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                <div key={day} className="text-center text-xs font-bold text-slate-400 uppercase">
                  {day}
                </div>
              ))}
            </div>

            {/* Days Grid */}
            <div className="grid grid-cols-7 gap-2">
              {/* Empty cells for padding before the 1st of the month */}
              {Array.from({ length: getFirstDayOffset(currentYear, currentMonth) }).map((_, i) => (
                <div key={`empty-${i}`} className="aspect-square"></div>
              ))}

              {/* Actual Days */}
              {heatmapData.map((item) => (
                <div
                  key={item.day}
                  className={`aspect-square rounded-md sm:rounded-lg flex items-center justify-center text-xs font-medium transition-all hover:scale-105 group relative cursor-default ${getIntensityColor(item.count)} ${item.count > 0 ? 'text-white' : 'text-slate-400 dark:text-slate-600'}`}
                >
                  {item.day}

                  {/* Tooltip on Hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                    {item.date}: {item.count} 句
                  </div>
                </div>
              ))}
            </div>

            {/* Legend */}
            <div className="flex justify-end items-center gap-2 mt-6 text-xs text-slate-500 dark:text-slate-400">
               <span>Less</span>
               <div className="flex gap-1">
                 <div className="w-3 h-3 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"></div>
                 <div className="w-3 h-3 rounded bg-indigo-200 dark:bg-indigo-900/40"></div>
                 <div className="w-3 h-3 rounded bg-indigo-400 dark:bg-indigo-700/60"></div>
                 <div className="w-3 h-3 rounded bg-indigo-600 dark:bg-indigo-500"></div>
               </div>
               <span>More</span>
            </div>
          </div>
        </div>

        {/* 3. 目标设定与进度 (Goal Setting) - 占 1/3 宽度 */}
        <div className="bg-white dark:bg-slate-800 p-6 sm:p-8 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col h-full">
           <div className="flex justify-between items-center mb-6">
             <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
               <Target className="text-emerald-500" size={20} />
               学习目标
             </h3>
             {!isEditingGoal ? (
               <button
                onClick={() => setIsEditingGoal(true)}
                className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors p-1"
                title="修改目标"
               >
                 <Edit2 size={16} />
               </button>
             ) : (
               <div className="flex gap-1">
                  <button onClick={handleSaveGoal} className="text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 p-1 rounded"><Check size={18} /></button>
                  <button onClick={() => setIsEditingGoal(false)} className="text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 p-1 rounded"><X size={18} /></button>
               </div>
             )}
           </div>

           {/* 周期切换 Tabs */}
           <div className="bg-slate-100 dark:bg-slate-900/50 p-1 rounded-xl flex mb-8">
             {['daily', 'weekly', 'monthly'].map(period => (
               <button
                 key={period}
                 onClick={() => setGoalPeriod(period as 'daily' | 'weekly' | 'monthly')}
                 className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all capitalize ${
                   goalPeriod === period
                     ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                     : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                 }`}
               >
                 {period}
               </button>
             ))}
           </div>

           {/* 进度圆环或条形展示 */}
           <div className="flex-1 flex flex-col items-center justify-center mb-6 relative">
              {/* 这里使用 CSS 实现简易圆环进度条，实际项目推荐使用 Recharts 或 svg */}
              <div className="relative w-48 h-48">
                 <svg className="w-full h-full transform -rotate-90">
                    {/* Background Circle */}
                    <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="none" className="text-slate-100 dark:text-slate-700" />
                    {/* Progress Circle */}
                    <circle
                      cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="none"
                      className={`${progressPercent >= 100 ? 'text-emerald-500' : 'text-indigo-500'} transition-all duration-1000 ease-out`}
                      strokeDasharray={552} // 2 * PI * 88
                      strokeDashoffset={552 - (552 * progressPercent) / 100}
                      strokeLinecap="round"
                    />
                 </svg>
                 <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-4xl font-bold text-slate-900 dark:text-white">{progressPercent}%</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 uppercase tracking-wider font-medium">Completed</span>
                 </div>
              </div>
           </div>

           {/* 数值展示与编辑 */}
           <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-100 dark:border-slate-700">
             <div className="flex justify-between items-center text-sm mb-2">
               <span className="text-slate-500 dark:text-slate-400">当前进度:</span>
               <span className="font-bold text-slate-900 dark:text-white">{currentGoal.current} {currentGoal.unit}</span>
             </div>
             <div className="flex justify-between items-center text-sm">
               <span className="text-slate-500 dark:text-slate-400">目标要求:</span>
               {isEditingGoal ? (
                 <div className="flex items-center gap-1">
                   <input
                     type="number"
                     value={tempGoalTarget}
                     onChange={(e) => setTempGoalTarget(parseInt(e.target.value) || 0)}
                     className="w-16 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded px-1 py-0.5 text-right font-bold outline-none focus:border-indigo-500"
                     autoFocus
                   />
                   <span className="text-slate-900 dark:text-white">{currentGoal.unit}</span>
                 </div>
               ) : (
                 <span className="font-bold text-slate-900 dark:text-white">{currentGoal.target} {currentGoal.unit}</span>
               )}
             </div>
           </div>

           {progressPercent >= 100 && (
             <div className="mt-4 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-xs font-bold px-3 py-2 rounded-lg flex items-center justify-center gap-2 animate-bounce">
               <Sparkles size={14} />
               太棒了！你已完成本周期目标！
             </div>
           )}
        </div>
      </div>
    </div>
  )
}

export default StatsPage