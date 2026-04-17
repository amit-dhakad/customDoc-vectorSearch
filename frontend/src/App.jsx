/**
 * App.jsx — THE SINGLE-PAGE APPLICATION (SPA) HEART.
 * 
 * DESIGN ARCHITECTURE:
 * ─────────────────────────────────────────────────────────────────────────────
 * This is the root of the React application. It manages the global routing 
 * (via react-router-dom) and the top-level workspace state (Sessions).
 * 
 * CORE RESPONSIBILITIES:
 * ──────────────────────────────────────────────────────────────
 * 1. WORKSPACE STATE: Fetches and maintains the list of active chat sessions.
 * 2. ROUTING: Orchestrates transitions between 'Chat View', 'Advanced Parsing', 
 *    and the 'Welcome Screen'.
 * 3. GLOBAL LOADING: Handles the initial application hydration state.
 * 
 * THE "MODULAR SHELL" PATTERN:
 * ──────────────────────────────────────────────────────────────
 * Instead of duplicating the Sidebar in every view, we use a `MainLayout` shell.
 * This ensures that navigation remains consistent while only the 'content' area 
 * swaps out, reducing re-renders and improving the "Glassmorphism" UI fluidity.
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams, Link } from 'react-router-dom';
import { 
  MessageSquare, 
  Settings, 
  Plus, 
  Trash2, 
  FileText, 
  Terminal as TerminalIcon,
  ChevronRight,
  Layers,
  ThumbsUp,
  ThumbsDown,
  Upload,
  Send,
  Loader2,
  Cpu,
  Zap,
  BarChart3,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from './api';
import './index.css';

// Components
import ChatWindow from './components/ChatWindow';
import AdvancedParsing from './components/AdvancedParsing';
import InterviewPrep from './components/InterviewPrep';
import MetricsDashboard from './components/MetricsDashboard';

// ── Device Status Badge ───────────────────────────────────────────────────────────
const DeviceBadge = () => {
  const [stats, setStats] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await api.getSystemStats();
      setStats(res.data);
    } catch { /* backend unreachable */ }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  const device = stats.device || 'cpu';
  const gpu    = stats.gpu;
  const isGpu  = device === 'cuda' || device === 'mps';
  const isWorking = stats.pipeline_status === 'PROCESSING';

  const color  = device === 'cuda' ? '#10b981'
               : device === 'mps'  ? '#f59e0b'
               : '#6b7280';

  const label  = device === 'cuda' ? 'GPU'
               : device === 'mps'  ? 'MPS'
               : 'CPU';

  return (
    <div style={{
      marginTop: '12px',
      padding: '10px 12px',
      borderRadius: '10px',
      background: isWorking ? `${color}22` : `${color}11`,
      border: `1px solid ${isWorking ? color : color + '33'}`,
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      transition: '0.3s ease',
    }}>
      {/* Pulse dot */}
      <div style={{ position: 'relative', flexShrink: 0 }}>
        {(isGpu || isWorking) && (
          <div style={{
            position: 'absolute', inset: '-3px',
            borderRadius: '50%',
            background: color,
            opacity: 0.25,
            animation: 'pulse 2s infinite',
          }} />
        )}
        <div style={{
          width: '8px', height: '8px',
          borderRadius: '50%',
          background: color,
        }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '11px', fontWeight: '700', color, display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isGpu ? <Zap size={11} /> : <Cpu size={11} />}
          {label} {isWorking ? 'Processing' : 'Active'}
        </div>
        {gpu && (
          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {gpu.name} · {gpu.vram_used_mb}MB / {gpu.vram_total_mb}MB
          </div>
        )}
        {!gpu && device === 'cuda' && (
          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>CUDA — Powering Intelligence</div>
        )}
        {device === 'cpu' && (
          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
            CPU {Math.round(stats.process_cpu || stats.cpu)}% · {stats.process_mem_mb || 0}MB Used ({Math.round(stats.memory)}%)
          </div>
        )}
      </div>
    </div>
  );
};

const Sidebar = ({ sessions, currentSession, onCreateSession, onDeleteSession }) => {
  return (
    <aside className="sidebar">
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '32px', padding: '0 8px', textDecoration: 'none', color: 'inherit' }}>
        <div style={{ width: '40px', height: '40px', background: 'var(--primary)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Layers size={24} color="white" />
        </div>
        <h2 style={{ fontSize: '18px', fontWeight: '700', letterSpacing: '-0.5px' }}>CustomDoc</h2>
      </Link>

      <button className="btn-primary" onClick={onCreateSession} style={{ width: '100%', marginBottom: '24px' }}>
        <Plus size={18} /> New Chat
      </button>

      <nav style={{ flex: 1, overflowY: 'auto' }}>
        <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', paddingLeft: '8px' }}>
          Recent Chats
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {sessions.map(session => (
            <div 
              key={session.id} 
              className={`glass-effect`} 
              style={{ 
                padding: '12px', 
                borderRadius: '12px', 
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                background: currentSession?.id === session.id ? 'var(--glass)' : 'transparent',
                borderColor: currentSession?.id === session.id ? 'var(--primary)' : 'transparent'
              }}
            >
              <MessageSquare size={16} color={currentSession?.id === session.id ? 'var(--primary)' : 'var(--text-dim)'} />
              <Link 
                to={`/chat/${session.id}`} 
                style={{ flex: 1, color: 'inherit', textDecoration: 'none', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
              >
                {session.title}
              </Link>
              <button 
                onClick={(e) => { e.preventDefault(); onDeleteSession(session.id); }}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', opacity: 0.5 }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </nav>

      <div style={{ marginTop: '24px', borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
        <Link 
          to="/advanced" 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px', 
            padding: '12px', 
            borderRadius: '12px', 
            color: 'var(--text-dim)', 
            textDecoration: 'none',
            fontSize: '14px'
          }}
        >
          <Settings size={18} />
          Advanced Parsing
        </Link>
        <Link 
          to="/metrics" 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px', 
            padding: '12px', 
            borderRadius: '12px', 
            color: 'var(--text-dim)', 
            textDecoration: 'none',
            fontSize: '14px'
          }}
        >
          <BarChart3 size={18} />
          Performance Metrics
        </Link>
        <DeviceBadge />
      </div>
    </aside>
  );
};

const App = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

const AppContent = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchSessions = async () => {
    try {
      const res = await api.getSessions();
      setSessions(res.data);
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleCreateSession = () => {
    const id = Math.random().toString(36).substring(7);
    navigate(`/chat/${id}`);
  };

  const handleDeleteSession = async (id) => {
    try {
      await api.deleteSession(id);
      fetchSessions();
      navigate('/');
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  if (loading) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Loader2 className="animate-spin" size={48} color="var(--primary)" />
    </div>
  );

  return (
    <div className="layout-container">
      <Routes>
        <Route path="/chat/:sessionId" element={<MainLayout sessions={sessions} onCreateSession={handleCreateSession} onDeleteSession={handleDeleteSession}><ChatWindow sessions={sessions} onRefreshSessions={fetchSessions} /></MainLayout>} />
        <Route path="/advanced" element={<MainLayout sessions={sessions} onCreateSession={handleCreateSession} onDeleteSession={handleDeleteSession}><AdvancedParsing /></MainLayout>} />
        <Route path="/metrics" element={<MainLayout sessions={sessions} onCreateSession={handleCreateSession} onDeleteSession={handleDeleteSession}><MetricsDashboard /></MainLayout>} />
        <Route path="/interview" element={<InterviewPrep />} />
        <Route path="/" element={<MainLayout sessions={sessions} onCreateSession={handleCreateSession} onDeleteSession={handleDeleteSession}><WelcomeView onStart={handleCreateSession}/></MainLayout>} />
      </Routes>
    </div>
  );
};

const MainLayout = ({ children, sessions, onCreateSession, onDeleteSession }) => {
  const { sessionId } = useParams();
  const currentSession = sessions.find(s => s.id === sessionId);

  return (
    <>
      <Sidebar 
        sessions={sessions} 
        currentSession={currentSession} 
        onCreateSession={onCreateSession} 
        onDeleteSession={onDeleteSession} 
      />
      <main className="main-content">
        {children}
      </main>
    </>
  );
};

const WelcomeView = ({ onStart }) => (
  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '40px' }}>
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <h1 style={{ fontSize: '48px', fontWeight: '800', marginBottom: '16px', background: 'linear-gradient(to right, #6366f1, #10b981)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
        Universal Document Intelligence
      </h1>
      <p style={{ fontSize: '18px', color: 'var(--text-dim)', maxWidth: '600px', marginBottom: '32px' }}>
        Upload any document, parse with precision, and extract insights using advanced vector search.
      </p>
      <button className="btn-primary" onClick={onStart} style={{ padding: '16px 32px', fontSize: '16px' }}>
        Start Exploration <ChevronRight size={20} />
      </button>
    </motion.div>
  </div>
);

export default App;
