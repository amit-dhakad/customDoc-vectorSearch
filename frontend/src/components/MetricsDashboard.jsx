import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BarChart3, 
  Activity, 
  Target, 
  Cpu, 
  ShieldCheck, 
  RefreshCcw, 
  Clock, 
  Zap,
  TrendingUp,
  Award,
  Info,
  Calendar,
  Layers,
  Search
} from 'lucide-react';
import { api } from '../api';

const ScoreRing = ({ value, label, color, icon: Icon }) => {
    const percentage = Math.round(value * 100);
    const radius = 35;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    return (
        <div className="flex flex-col items-center justify-center p-6 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 hover:bg-white/10 transition-colors group">
            <div className="relative w-24 h-24 mb-4">
                <svg className="w-full h-full transform -rotate-90">
                    <circle
                        cx="48"
                        cy="48"
                        r={radius}
                        fill="transparent"
                        stroke="rgba(255,255,255,0.05)"
                        strokeWidth="8"
                    />
                    <motion.circle
                        cx="48"
                        cy="48"
                        r={radius}
                        fill="transparent"
                        stroke={color}
                        strokeWidth="8"
                        strokeDasharray={circumference}
                        initial={{ strokeDashoffset: circumference }}
                        animate={{ strokeDashoffset: offset }}
                        transition={{ duration: 1.5, ease: "easeOut" }}
                        strokeLinecap="round"
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-xl font-bold text-white">{percentage}%</span>
                </div>
            </div>
            <div className="flex items-center gap-2 text-sm font-medium text-white/60 group-hover:text-white transition-colors">
                <Icon size={16} />
                {label}
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, unit, icon: Icon, color }) => (
    <div className="p-6 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 hover:bg-white/10 transition-colors">
        <div className="flex items-center justify-between mb-4">
            <div className={`p-2 rounded-lg bg-${color}-500/20 text-${color}-400`}>
                <Icon size={20} />
            </div>
            <span className="text-xs font-medium text-white/30 uppercase tracking-wider">{label}</span>
        </div>
        <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">{value}</span>
            <span className="text-sm font-medium text-white/40">{unit}</span>
        </div>
    </div>
);

const Sparkline = ({ data, color, height = 100 }) => {
    if (!data || data.length < 2) return null;
    
    const max = Math.max(...data, 0.01);
    const min = Math.min(...data);
    const range = max - min || 1;
    const padding = 5;
    
    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = padding + (height - 2 * padding) * (1 - (val - min) / range);
        return `${x},${y}`;
    }).join(' ');

    return (
        <div className="w-full" style={{ height }}>
            <svg viewBox={`0 0 100 ${height}`} className="w-full h-full preserve-3d" preserveAspectRatio="none">
                <defs>
                    <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                        <stop offset="100%" stopColor={color} stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path
                    d={`M 0,${height} L ${points} L 100,${height} Z`}
                    fill={`url(#grad-${color})`}
                />
                <motion.polyline
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    points={points}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, ease: "easeInOut" }}
                />
            </svg>
        </div>
    );
};

const MetricsDashboard = () => {
    const [summary, setSummary] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMetrics();
    }, []);

    const fetchMetrics = async () => {
        setLoading(true);
        try {
            const [summaryRes, historyRes] = await Promise.all([
                api.getMetricsSummary(),
                api.getMetricsHistory(7)
            ]);
            setSummary(summaryRes.data);
            setHistory(historyRes.data);
        } catch (err) {
            console.error("Failed to fetch metrics:", err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div className="flex items-center justify-center h-full">
            <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="text-blue-400"
            >
                <RefreshCcw size={32} />
            </motion.div>
        </div>
    );

    return (
        <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto custom-scrollbar">
            <header className="flex items-center justify-between mb-10">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Activity className="text-blue-400" />
                        RAG Performance Analytics
                        <span className="text-xs font-normal px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full border border-blue-500/30">Tier 1 Production</span>
                    </h1>
                    <p className="text-white/40 mt-2">Real-time observability and quality scoring (RAGAS)</p>
                </div>
                <button 
                    onClick={fetchMetrics}
                    className="p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/60 hover:text-white transition-all active:scale-95"
                >
                    <RefreshCcw size={20} />
                </button>
            </header>

            {/* Quality Rings */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                <ScoreRing 
                    value={summary?.quality?.avg_faithfulness} 
                    label="Faithfulness" 
                    color="#60A5FA" 
                    icon={ShieldCheck} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_relevancy} 
                    label="Answer Relevancy" 
                    color="#F472B6" 
                    icon={Target} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_precision} 
                    label="Context Precision" 
                    color="#34D399" 
                    icon={Award} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_recall} 
                    label="Context Recall" 
                    color="#A78BFA" 
                    icon={TrendingUp} 
                />
            </section>

            {/* Performance Stats & Trends */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
                <div className="lg:col-span-2 space-y-8">
                    {/* Latency Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <MetricCard 
                            label="Avg Retrieval Latency" 
                            value={summary?.latency?.avg_retrieval_ms} 
                            unit="ms" 
                            color="emerald" 
                            icon={Zap} 
                        />
                        <MetricCard 
                            label="Avg Generation Latency" 
                            value={summary?.latency?.avg_generation_ms} 
                            unit="ms" 
                            color="blue" 
                            icon={Clock} 
                        />
                    </div>

                    {/* Quality Trends Chart */}
                    <div className="p-6 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-white font-bold flex items-center gap-2">
                                <TrendingUp size={18} className="text-blue-400" />
                                7-Day Quality Trends
                            </h3>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-blue-400" />
                                    <span className="text-xs text-white/40">Faithfulness</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-pink-400" />
                                    <span className="text-xs text-white/40">Relevancy</span>
                                </div>
                            </div>
                        </div>
                        
                        <div className="space-y-4">
                            <Sparkline data={history.map(h => h.faithfulness)} color="#60A5FA" />
                            <Sparkline data={history.map(h => h.relevancy)} color="#F472B6" />
                        </div>
                        
                        <div className="flex justify-between mt-4">
                            {history.length > 0 ? (
                                <>
                                    <span className="text-[10px] text-white/20 uppercase font-bold">{history[0].day}</span>
                                    <span className="text-[10px] text-white/20 uppercase font-bold">{history[history.length-1].day}</span>
                                </>
                            ) : (
                                <span className="text-[10px] text-white/20 uppercase">No history data available</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Metrics Glossary / Info Panel */}
                <div className="space-y-6">
                    <div className="p-6 bg-gradient-to-br from-blue-500/10 to-purple-500/10 backdrop-blur-md rounded-2xl border border-white/10">
                        <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                            <Info size={18} className="text-blue-400" />
                            RAGAS Glossary
                        </h3>
                        <div className="space-y-6">
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <ShieldCheck size={14} className="text-blue-400" />
                                    <span className="text-xs font-bold text-white/90">Faithfulness</span>
                                </div>
                                <p className="text-[11px] text-white/50 leading-relaxed">
                                    Verifies that the generated answer is derived solely from the retrieved context. Low scores indicate potential hallucinations.
                                </p>
                            </div>
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <Target size={14} className="text-pink-400" />
                                    <span className="text-xs font-bold text-white/90">Answer Relevancy</span>
                                </div>
                                <p className="text-[11px] text-white/50 leading-relaxed">
                                    Quantifies how pertinent the generated answer is to the original query. Penalizes redundant or off-topic information.
                                </p>
                            </div>
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <Layers size={14} className="text-emerald-400" />
                                    <span className="text-xs font-bold text-white/90">Context Precision</span>
                                </div>
                                <p className="text-[11px] text-white/50 leading-relaxed">
                                    Measures the signal-to-noise ratio in retrieved fragments. High scores mean the top results contained the necessary information.
                                </p>
                            </div>
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <Search size={14} className="text-purple-400" />
                                    <span className="text-xs font-bold text-white/90">Context Recall</span>
                                </div>
                                <p className="text-[11px] text-white/50 leading-relaxed">
                                    Checks if all facets of the required information were present in the retrieved context. Essential for complex multi-part queries.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* System Volume */}
                    <div className="p-6 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10">
                        <div className="flex items-center justify-between">
                            <div className="flex flex-col">
                                <span className="text-xs text-white/30 uppercase tracking-widest font-bold">Processed Responses</span>
                                <span className="text-2xl font-bold text-white mt-1">{summary?.volume?.total_assistant_responses || 0}</span>
                            </div>
                            <BarChart3 size={32} className="text-white/10" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MetricsDashboard;
