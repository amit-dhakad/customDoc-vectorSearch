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
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from './api';
import './index.css';

// Components
import ChatWindow from './components/ChatWindow';
import AdvancedParsing from './components/AdvancedParsing';

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
