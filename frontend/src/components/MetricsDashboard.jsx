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
        <div className="dashboard-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ position: 'relative', width: '96px', height: '96px', marginBottom: '16px' }}>
                <svg style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
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
                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: '20px', fontBold: '800', color: '#fff' }}>{percentage}%</span>
                </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: '600', color: 'var(--text-dim)' }}>
                <Icon size={14} />
                {label}
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, unit, icon: Icon, colorClass }) => (
    <div className="dashboard-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'between', marginBottom: '16px' }}>
            <div className={`icon-box ${colorClass}`}>
                <Icon size={20} />
            </div>
            <span className="metric-label" style={{ marginLeft: 'auto' }}>{label}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
            <span className="metric-value">{value}</span>
            <span className="metric-unit">{unit}</span>
        </div>
    </div>
);

const Sparkline = ({ data, color, height = 100 }) => {
    if (!data || data.length < 2) return (
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '10px' }}>
            Insufficient trend data
        </div>
    );
    
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
        <div style={{ height, width: '100%', marginTop: '12px', marginBottom: '12px' }}>
            <svg viewBox={`0 0 100 ${height}`} style={{ width: '100%', height: '100%' }} preserveAspectRatio="none">
                <defs>
                    <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={color} stopOpacity="0.3" />
                        <stop offset="100%" stopColor={color} stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path
                    d={`M 0,${height} L ${points} L 100,${height} Z`}
                    fill={`url(#grad-${color.replace('#', '')})`}
                />
                <motion.polyline
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    points={points}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, ease: "easeInOut" }}
                    strokeLinecap="round"
                    strokeLinejoin="round"
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                style={{ color: 'var(--primary)' }}
            >
                <RefreshCcw size={32} />
            </motion.div>
        </div>
    );

    return (
        <div className="metrics-container custom-scrollbar">
            <header className="metrics-header">
                <div>
                    <h1 style={{ fontSize: '30px', fontWeight: '800', color: '#fff', display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
                        <Activity color="var(--primary)" />
                        Intelligence Analytics
                        <span style={{ fontSize: '10px', fontWeight: '700', padding: '4px 10px', background: 'rgba(99,102,241,0.15)', color: 'var(--primary)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '30px' }}>
                            Tier 1 PRO
                        </span>
                    </h1>
                    <p style={{ color: 'var(--text-dim)', marginTop: '8px', fontSize: '15px' }}>Production-grade observability & quality metrics (RAGAS)</p>
                </div>
                <button 
                    onClick={fetchMetrics}
                    style={{ padding: '12px', background: 'var(--glass)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                    <RefreshCcw size={18} />
                </button>
            </header>

            {/* Quality Rounds */}
            <section className="metrics-grid-4">
                <ScoreRing 
                    value={summary?.quality?.avg_faithfulness || 0} 
                    label="Faithfulness" 
                    color="#60A5FA" 
                    icon={ShieldCheck} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_relevancy || 0} 
                    label="Answer Relevancy" 
                    color="#F472B6" 
                    icon={Target} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_precision || 0} 
                    label="Context Precision" 
                    color="#34D399" 
                    icon={Award} 
                />
                <ScoreRing 
                    value={summary?.quality?.avg_recall || 0} 
                    label="Context Recall" 
                    color="#A78BFA" 
                    icon={TrendingUp} 
                />
            </section>

            {/* Sub grids for latency and history */}
            <div className="metrics-main-grid">
                <div>
                    <div className="stats-sub-grid">
                        <MetricCard 
                            label="Avg Retrieval Latency" 
                            value={summary?.latency?.avg_retrieval_ms || 0} 
                            unit="ms" 
                            colorClass="color-emerald" 
                            icon={Zap} 
                        />
                        <MetricCard 
                            label="Avg Generation Latency" 
                            value={summary?.latency?.avg_generation_ms || 0} 
                            unit="ms" 
                            colorClass="color-blue" 
                            icon={Clock} 
                        />
                    </div>

                    <div className="dashboard-card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                            <h3 style={{ fontSize: '16px', fontWeight: '800', color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <TrendingUp size={18} color="var(--primary)" />
                                7-Day Performance Trends
                            </h3>
                            <div style={{ display: 'flex', gap: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#60A5FA' }} />
                                    <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Faithfulness</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#F472B6' }} />
                                    <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Relevancy</span>
                                </div>
                            </div>
                        </div>

                        <Sparkline data={history.map(h => h.faithfulness)} color="#60A5FA" />
                        <Sparkline data={history.map(h => h.relevancy)} color="#F472B6" />

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                            {history.length > 0 ? (
                                <>
                                    <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', fontWeight: '800', textTransform: 'uppercase' }}>{history[0].day}</span>
                                    <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', fontWeight: '800', textTransform: 'uppercase' }}>{history[history.length-1].day}</span>
                                </>
                            ) : (
                                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)' }}>No history available</span>
                            )}
                        </div>
                    </div>
                </div>

                <aside>
                    <div className="dashboard-card" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(167,139,250,0.08) 100%)' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: '800', color: '#fff', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Info size={18} color="var(--primary)" />
                            Quality Matrix
                        </h3>
                        <div className="glossary-item">
                            <h4><ShieldCheck size={14} color="#60A5FA" /> Faithfulness</h4>
                            <p>Ensures the answer is grounded in the retrieved documents, preventing AI hallucinations.</p>
                        </div>
                        <div className="glossary-item">
                            <h4><Target size={14} color="#F472B6" /> Relevancy</h4>
                            <p>Measures how effectively the generated text addresses the user's specific question.</p>
                        </div>
                        <div className="glossary-item">
                            <h4><Layers size={14} color="#34D399" /> Precision</h4>
                            <p>Evaluates if the top retrieved fragments contain the actual signal required for the answer.</p>
                        </div>
                        <div className="glossary-item">
                            <h4><Search size={14} color="#A78BFA" /> Recall</h4>
                            <p>Confirms if all necessary aspects of the ground truth were found in the context.</p>
                        </div>
                    </div>

                    <div className="dashboard-card" style={{ marginTop: '24px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div className="metric-label" style={{ marginBottom: '4px' }}>Total Interactions</div>
                                <div className="metric-value">{summary?.volume?.total_assistant_responses || 0}</div>
                            </div>
                            <BarChart3 size={32} style={{ opacity: 0.1 }} />
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
};

export default MetricsDashboard;
