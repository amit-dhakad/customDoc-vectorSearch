/**
 * ChatWindow.jsx — THE CONVERSATIONAL INTELLIGENCE INTERFACE.
 *
 * Connects the user to RAG-powered answers from their uploaded documents.
 * Model selector fetches live Ollama models via the backend proxy.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Send, Upload, ThumbsUp, ThumbsDown, Bot, User,
  FileText, X, MessageSquare, ChevronDown, Cpu, RefreshCw,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, WS_URL } from '../api';

// ── Fallback when Ollama is unreachable ────────────────────────────────────
const FALLBACK_MODELS = [
  { id: 'llama3', label: 'Llama 3' },
  { id: 'gemma',  label: 'Gemma'  },
];

const MODEL_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const getModelColor = (idx) => MODEL_COLORS[idx % MODEL_COLORS.length];

// ── Thinking animation ─────────────────────────────────────────────────────
const ThinkingBubble = ({ modelLabel }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -5 }}
    className="ai-message"
    style={{ display: 'flex', gap: '12px', padding: '16px' }}
  >
    <div style={{ padding: '8px', background: 'var(--glass)', borderRadius: '8px', height: 'fit-content' }}>
      <Bot size={16} color="var(--primary)" />
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {[0, 1, 2].map(i => (
          <motion.div
            key={i}
            animate={{ 
              scale: [1, 1.3, 1],
              opacity: [0.3, 1, 0.3],
            }}
            transition={{ 
              duration: 1.2, 
              repeat: Infinity, 
              delay: i * 0.2, 
              ease: 'easeInOut' 
            }}
            style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary)' }}
          />
        ))}
        <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontWeight: '600', letterSpacing: '0.2px' }}>
          {modelLabel} is processing…
        </span>
      </div>
      <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic', opacity: 0.8 }}>
        Retrieving facts and generating insight
      </div>
    </div>
  </motion.div>
);

// ── Upload overlay ─────────────────────────────────────────────────────────
const UploadOverlay = ({ logs }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    style={{
      position: 'absolute', inset: 0,
      background: 'rgba(var(--bg-rgb), 0.85)',
      backdropFilter: 'blur(12px)',
      zIndex: 5,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      textAlign: 'center', padding: '20px',
    }}
  >
    <div style={{ position: 'relative', width: '100px', height: '100px', marginBottom: '32px' }}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          border: '3px solid transparent',
          borderTopColor: 'var(--primary)', borderRightColor: 'rgba(99,102,241,0.3)',
        }}
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute', inset: '12px', borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: '#10b981', borderLeftColor: 'rgba(16,185,129,0.3)',
        }}
      />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 1.5, repeat: Infinity }}>
          <FileText size={28} color="var(--primary)" />
        </motion.div>
      </div>
    </div>

    <h3 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '8px', letterSpacing: '-0.5px' }}>Analyzing Intelligence</h3>
    <p style={{ color: 'var(--text-dim)', fontSize: '15px', maxWidth: '340px', marginBottom: '32px', lineHeight: 1.5 }}>
      Extracting semantic structure and indexing vectors for RAG retrieval.
    </p>

    {/* Live Log Terminal */}
    <div style={{
      width: '100%', maxWidth: '400px',
      background: 'rgba(0,0,0,0.4)',
      borderRadius: '16px',
      border: '1px solid var(--border)',
      padding: '20px',
      textAlign: 'left',
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: '12px',
      maxHeight: '120px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      <div style={{ fontSize: '10px', fontWeight: '800', color: 'var(--primary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary)', animation: 'pulse 1.5s infinite' }} />
        Pipeline Stream
      </div>
      <AnimatePresence mode="popLayout">
        {logs.slice(-3).map((log, i) => (
          <motion.div
            key={log + i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1 - (2 - i) * 0.3, x: 0 }}
            style={{ color: i === logs.slice(-3).length - 1 ? 'var(--text)' : 'var(--text-dim)', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {log.replace(/^\[.*?\]\s*/, '> ')}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  </motion.div>
);

// ── Model selector ─────────────────────────────────────────────────────────
const ModelSelector = ({ selectedModel, onModelChange, models, loadingModels, onRefresh }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const idx = models.findIndex(m => m.id === selectedModel);
  const current = models[idx] || models[0];
  const currentColor = getModelColor(idx >= 0 ? idx : 0);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '6px' }}>
      {/* Selector button */}
      <button
        onClick={() => setOpen(o => !o)}
        disabled={loadingModels}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 14px', borderRadius: '10px',
          border: `1px solid ${currentColor}55`,
          background: `${currentColor}11`,
          color: currentColor,
          fontSize: '13px', fontWeight: '600',
          cursor: loadingModels ? 'wait' : 'pointer',
          transition: 'all 0.2s', minWidth: '130px',
        }}
      >
        <Cpu size={14} />
        {loadingModels ? 'Loading…' : (current?.label || 'Pick Model')}
        {!loadingModels && (
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={14} />
          </motion.div>
        )}
      </button>

      {/* Refresh */}
      <button
        onClick={onRefresh}
        title="Refresh model list from Ollama"
        style={{
          padding: '8px', borderRadius: '8px',
          border: '1px solid var(--border)',
          background: 'transparent', color: 'var(--text-dim)',
          cursor: 'pointer', display: 'flex', alignItems: 'center',
        }}
      >
        <motion.div
          animate={loadingModels ? { rotate: 360 } : { rotate: 0 }}
          transition={loadingModels ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}
        >
          <RefreshCw size={13} />
        </motion.div>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            style={{
              position: 'absolute', top: 'calc(100% + 8px)', left: 0,
              minWidth: '240px', background: 'var(--bg)',
              border: '1px solid var(--border)', borderRadius: '14px',
              overflow: 'hidden', boxShadow: '0 16px 40px rgba(0,0,0,0.25)', zIndex: 50,
            }}
          >
            <div style={{ padding: '10px 16px 6px', fontSize: '10px', fontWeight: '800', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Ollama Models ({models.length})
            </div>
            {models.length === 0 && (
              <div style={{ padding: '16px', fontSize: '13px', color: 'var(--text-dim)', textAlign: 'center' }}>
                No models found. Is Ollama running?
              </div>
            )}
            {models.map((m, i) => {
              const color = getModelColor(i);
              return (
                <div
                  key={m.id}
                  onClick={() => { onModelChange(m.id); setOpen(false); }}
                  style={{
                    padding: '10px 16px', cursor: 'pointer',
                    background: selectedModel === m.id ? `${color}15` : 'transparent',
                    borderLeft: selectedModel === m.id ? `3px solid ${color}` : '3px solid transparent',
                    transition: 'background 0.15s',
                    display: 'flex', flexDirection: 'column', gap: '2px',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = `${color}10`}
                  onMouseLeave={e => e.currentTarget.style.background = selectedModel === m.id ? `${color}15` : 'transparent'}
                >
                  <span style={{ fontWeight: '700', fontSize: '13px', color }}>{m.label}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'monospace' }}>{m.id}</span>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────
const ChatWindow = ({ sessions = [], onRefreshSessions }) => {
  const { sessionId } = useParams();
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [uploading, setUploading]     = useState(false);
  const [loading, setLoading]         = useState(false);
  const [documents, setDocuments]     = useState([]);
  const [showDocuments, setShowDocuments] = useState(false);
  const [selectedModel, setSelectedModel]       = useState('llama3');
  const [availableModels, setAvailableModels]   = useState(FALLBACK_MODELS);
  const [loadingModels, setLoadingModels]       = useState(false);
  const scrollRef  = useRef(null);
  const fileInputRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const clientId = useRef(Math.random().toString(36).substring(7)).current;
  const ws = useRef(null);
  const sessionCreationPromise = useRef(null);

  const currentModelLabel = availableModels.find(m => m.id === selectedModel)?.label || selectedModel || 'AI';

  // ── Fetch Ollama models ──────────────────────────────────────────────────
  const fetchOllamaModels = async () => {
    setLoadingModels(true);
    try {
      const res = await api.getOllamaModels();
      const models = res.data?.models || [];
      if (models.length > 0) {
        setAvailableModels(models);
        if (!models.find(m => m.id === selectedModel)) {
          setSelectedModel(models[0].id);
        }
      } else {
        setAvailableModels(FALLBACK_MODELS);
      }
    } catch {
      setAvailableModels(FALLBACK_MODELS);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => { fetchOllamaModels(); }, []);

  // ── Session helpers ──────────────────────────────────────────────────────
  const ensureSessionExists = async () => {
    if (sessionCreationPromise.current) {
      await sessionCreationPromise.current;
      return;
    }
    const exists = sessions.find(s => s.id === sessionId);
    if (!exists && !sessionCreationPromise.current) {
      sessionCreationPromise.current = api.createSession(sessionId, 'New Chat');
      try {
        await sessionCreationPromise.current;
        if (onRefreshSessions) await onRefreshSessions();
      } catch (err) {
        console.error('[ChatWindow] Failed to finalize session:', err);
        throw err;
      } finally {
        sessionCreationPromise.current = null;
      }
    }
  };

  const fetchMessages = async () => {
    try {
      const res = await api.getMessages(sessionId);
      setMessages(res.data);
    } catch (err) {
      console.error('Failed to fetch messages', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await api.getDocuments(sessionId);
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to fetch documents', err);
    }
  };

  useEffect(() => {
    if (sessionId) {
      fetchMessages();
      fetchDocuments();
    }
  }, [sessionId]);

  useEffect(() => {
    ws.current = new WebSocket(`${WS_URL}/${clientId}`);
    ws.current.onmessage = (event) => { setLogs(prev => [...prev, event.data]); };
    return () => ws.current?.close();
  }, [clientId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Send message ─────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input;
    setInput('');
    setLoading(true);
    setMessages(prev => [...prev, { id: `tmp-${Date.now()}`, role: 'user', content: userMsg }]);

    try {
      await ensureSessionExists();
      await api.askQuestion(sessionId, userMsg, selectedModel);
      await fetchMessages();
    } catch (err) {
      console.error('Failed to send message', err);
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`, role: 'assistant',
        content: '⚠️ Failed to get a response. Please check backend logs.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // ── File upload ──────────────────────────────────────────────────────────
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', 'fitz');
    formData.append('ocr', 'true');
    try {
      await ensureSessionExists();
      setLogs(['Initializing parsing pipeline…']);
      formData.append('session_id', sessionId);
      formData.append('client_id', clientId);
      formData.append('auto_chunk', 'true'); // Ensure background vectorization for RAG
      await api.parseDocument(formData);
      await api.sendMessage(
        sessionId, 'assistant',
        `✅ **${file.name}** has been processed successfully!\n\nYou can now ask questions about its content.`
      );
      fetchMessages();
      fetchDocuments();
    } catch (err) {
      console.error('Upload failed', err);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleFeedback = async (messageId, isPositive) => {
    try { await api.submitFeedback(messageId, isPositive); }
    catch (err) { console.error('Feedback failed', err); }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Header */}
      <header style={{
        padding: '12px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--bg)', gap: '12px', flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquare size={18} color="var(--primary)" />
          <span style={{ fontWeight: '600' }}>Chat Session</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <ModelSelector
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
            models={availableModels}
            loadingModels={loadingModels}
            onRefresh={fetchOllamaModels}
          />
          <button
            className="glass-effect"
            onClick={() => { setShowDocuments(!showDocuments); fetchDocuments(); }}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '8px 14px', borderRadius: '10px', fontSize: '13px',
              fontWeight: '500', color: 'var(--text)', border: '1px solid var(--border)', cursor: 'pointer',
            }}
          >
            <FileText size={15} />
            Docs {documents.length > 0 && `(${documents.length})`}
          </button>
        </div>
      </header>

      {/* Messages */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, overflowY: 'auto', padding: '32px 20px' }}>
          <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column' }}>
            {/* 
              Show WelcomeState ONLY if there are no messages AND no documents yet.
              If documents exist but no messages (rarely happens now due to seeding), 
              we still allow the chat interface to show so the user can just start typing.
            */}
            {messages.length === 0 && documents.length === 0 ? (
              <WelcomeState onUpload={() => fileInputRef.current?.click()} />
            ) : (
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={msg.id || i}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={`message-bubble ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}
                  >
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ padding: '8px', background: 'var(--glass)', borderRadius: '8px', height: 'fit-content' }}>
                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} color="var(--primary)" />}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        {msg.role === 'assistant' && (
                          <div style={{ marginTop: '12px', display: 'flex', gap: '8px', opacity: 0.6 }}>
                            <button onClick={() => handleFeedback(msg.id, true)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                              <ThumbsUp size={14} />
                            </button>
                            <button onClick={() => handleFeedback(msg.id, false)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                              <ThumbsDown size={14} />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}

            <AnimatePresence>
              {loading && <ThinkingBubble modelLabel={currentModelLabel} />}
            </AnimatePresence>
            <div ref={scrollRef} />
          </div>
        </div>

        {/* Upload overlay */}
        <AnimatePresence>
          {uploading && <UploadOverlay logs={logs} />}
        </AnimatePresence>
      </div>

      {/* Input bar */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper glass-effect">
          <label style={{ cursor: 'pointer', padding: '12px' }}>
            <input type="file" style={{ display: 'none' }} onChange={handleFileUpload} ref={fileInputRef} />
            <Upload size={20} color={uploading ? 'var(--primary)' : 'var(--text-dim)'} className={uploading ? 'animate-bounce' : ''} />
          </label>
          <input
            className="input-field"
            placeholder={`Ask ${currentModelLabel} about your documents…`}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={loading}
          />
          <button className="btn-primary" onClick={handleSend} style={{ width: '45px', padding: '0' }} disabled={loading || !input.trim()}>
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* Documents slide-over */}
      <AnimatePresence>
        {showDocuments && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowDocuments(false)}
              style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.3)', backdropFilter: 'blur(4px)', zIndex: 10 }}
            />
            <motion.div
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              style={{
                position: 'absolute', top: 0, right: 0, bottom: 0, width: '400px',
                background: 'var(--bg)', borderLeft: '1px solid var(--border)',
                zIndex: 11, padding: '32px', boxShadow: '-10px 0 30px rgba(0,0,0,0.1)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: '700' }}>Session Documents</h3>
                <button onClick={() => setShowDocuments(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}>
                  <X size={24} />
                </button>
              </div>

              {documents.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-dim)' }}>
                  <FileText size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                  <p>No documents linked to this session.</p>
                  <p style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>Upload a file or use Advanced Parsing and navigate here.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {documents.map(doc => (
                    <div key={doc.id} className="glass-effect" style={{ padding: '16px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ padding: '10px', background: 'var(--primary)', borderRadius: '10px', color: 'white' }}>
                        <FileText size={20} />
                      </div>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={{ fontWeight: '600', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.filename}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                          {new Date(doc.created_at).toLocaleDateString()} · {doc.file_type || 'Unknown'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

// ── Welcome screen ─────────────────────────────────────────────────────────
const WelcomeState = ({ onUpload }) => (
  <div style={{ padding: '80px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      style={{ width: '100%', maxWidth: '460px' }}
    >
      {/* Bot icon */}
      <div style={{
        width: '80px', height: '80px',
        background: 'var(--glass)',
        borderRadius: '24px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 28px',
        border: '1px solid var(--border)',
      }}>
        <Bot size={40} color="var(--primary)" />
      </div>

      <h2 style={{ fontSize: '28px', fontWeight: '800', marginBottom: '12px' }}>Start a New Chat</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: '15px', maxWidth: '380px', margin: '0 auto 40px', lineHeight: 1.6 }}>
        Upload a document and I'll answer questions about it using the content you've provided.
      </p>

      {/* Single prominent upload card */}
      <motion.div
        onClick={onUpload}
        whileHover={{ y: -4, boxShadow: '0 20px 40px rgba(99,102,241,0.18)' }}
        whileTap={{ scale: 0.98 }}
        className="glass-effect"
        style={{
          padding: '36px 32px',
          borderRadius: '24px',
          cursor: 'pointer',
          border: '1.5px dashed rgba(99,102,241,0.45)',
          background: 'rgba(99,102,241,0.04)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <div style={{
          width: '56px', height: '56px',
          background: 'rgba(99,102,241,0.12)',
          borderRadius: '16px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Upload size={26} color="var(--primary)" />
        </div>
        <div>
          <div style={{ fontWeight: '700', fontSize: '17px', marginBottom: '4px' }}>Upload a Document</div>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)' }}>PDF, DOCX, TXT — drag &amp; drop or click to browse</div>
        </div>
        <div style={{
          fontSize: '12px',
          color: 'var(--primary)',
          fontWeight: '600',
          padding: '6px 16px',
          background: 'rgba(99,102,241,0.1)',
          borderRadius: '20px',
          border: '1px solid rgba(99,102,241,0.2)',
        }}>
          Click to browse files
        </div>
      </motion.div>

      {/* Subtle hint — input bar is always available */}
      <p style={{ marginTop: '24px', fontSize: '12px', color: 'var(--text-dim)', opacity: 0.7 }}>
        Already have data? Just type your question in the bar below.
      </p>
    </motion.div>
  </div>
);

export default ChatWindow;

