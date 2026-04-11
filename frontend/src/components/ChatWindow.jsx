import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Upload, ThumbsUp, ThumbsDown, Loader2, Bot, User, FileText, X, ChevronRight, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, WS_URL } from '../api';

const ChatWindow = ({ sessions = [], onRefreshSessions }) => {
  const { sessionId } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [showDocuments, setShowDocuments] = useState(false);
  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const clientId = useRef(Math.random().toString(36).substring(7)).current;
  const ws = useRef(null);
  const sessionCreationPromise = useRef(null);

  const ensureSessionExists = async () => {
    // 1. If creation is already in progress, wait for it to complete
    if (sessionCreationPromise.current) {
      console.log(`[ChatWindow] Creation in progress for ${sessionId}, waiting...`);
      await sessionCreationPromise.current;
      return;
    }

    // 2. Double check if it exists now (it might have been created while we waited above)
    const exists = sessions.find(s => s.id === sessionId);
    if (!exists) {
      console.log(`[ChatWindow] Lazily creating session ${sessionId}`);
      
      // Store the promise in the ref so other calls can await it
      sessionCreationPromise.current = api.createSession(sessionId, "New Chat");
      
      try {
        await sessionCreationPromise.current;
        if (onRefreshSessions) await onRefreshSessions();
        console.log(`[ChatWindow] Session ${sessionId} finalized.`);
      } catch (err) {
        console.error("[ChatWindow] Failed to finalize session:", err);
        throw err;
      } finally {
        // Clear the promise ref regardless of outcome
        sessionCreationPromise.current = null;
      }
    }
  };

  const fetchMessages = async () => {
    if (!sessions.find(s => s.id === sessionId)) return;
    try {
      const res = await api.getMessages(sessionId);
      setMessages(res.data);
    } catch (err) {
      console.error("Failed to fetch messages", err);
    }
  };

  const fetchDocuments = async () => {
    if (!sessions.find(s => s.id === sessionId)) return;
    try {
      const res = await api.getDocuments(sessionId);
      setDocuments(res.data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
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
    ws.current.onmessage = (event) => {
      setLogs(prev => [...prev, event.data]);
    };
    return () => ws.current?.close();
  }, [clientId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setInput('');
    try {
      await ensureSessionExists();
      // 1. Save user message
      await api.sendMessage(sessionId, 'user', userMsg);
      fetchMessages();

      // 2. Simulate AI response (Mock for now as backend LLM is pending)
      setTimeout(async () => {
        await api.sendMessage(sessionId, 'assistant', `I've received your message: "${userMsg}". Vector search and LLM integration are coming soon!`);
        fetchMessages();
        setLoading(false);
      }, 1000);

    } catch (err) {
      console.error("Failed to send message", err);
      setLoading(false);
    }
  };

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
      setLogs(["Initializing parsing pipeline..."]);
      formData.append('session_id', sessionId);
      formData.append('client_id', clientId);
      const res = await api.parseDocument(formData);
      await api.sendMessage(sessionId, 'assistant', `✅ **${file.name}** has been processed successfully!\n\nI've extracted the core intelligence from your document. You can now ask questions about its content, or visit the **Advanced Parsing** section to see the raw extraction details and fine-tune engines.`);
      fetchMessages();
      fetchDocuments();
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
  };

  const handleFeedback = async (messageId, isPositive) => {
    try {
      await api.submitFeedback(messageId, isPositive);
      // Update UI state locally if needed
    } catch (err) {
      console.error("Feedback failed", err);
    }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Header with Documents Button */}
      <header style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquare size={18} color="var(--primary)" />
          <span style={{ fontWeight: '600' }}>Chat Session</span>
        </div>
        <button 
          className="glass-effect" 
          onClick={() => setShowDocuments(!showDocuments)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '8px 16px', 
            borderRadius: '8px', 
            fontSize: '14px', 
            fontWeight: '500',
            color: 'var(--text)',
            border: '1px solid var(--border)'
          }}
        >
          <FileText size={16} /> Documents {documents.length > 0 && `(${documents.length})`}
        </button>
      </header>

      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, overflowY: 'auto', padding: '40px 20px' }}>
          <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column' }}>
            {messages.length === 0 ? (
              <WelcomeState onUpload={() => fileInputRef.current?.click()} onChat={() => setInput('Hello! how can you help me with my data?')} />
            ) : (
              <AnimatePresence>
                {messages.map((msg, i) => (
                  <motion.div
                    key={msg.id || i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`message-bubble ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}
                    style={{ position: 'relative' }}
                  >
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ padding: '8px', background: 'var(--glass)', borderRadius: '8px', height: 'fit-content' }}>
                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        
                        {msg.role === 'assistant' && (
                          <div style={{ marginTop: '12px', display: 'flex', gap: '8px', opacity: 0.6 }}>
                            <button 
                              onClick={() => handleFeedback(msg.id, true)} 
                              style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
                            >
                              <ThumbsUp size={14} />
                            </button>
                            <button 
                              onClick={() => handleFeedback(msg.id, false)} 
                              style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
                            >
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
            {loading && (
               <div style={{ display: 'flex', gap: '12px', padding: '16px' }}>
                  <Bot size={16} color="var(--primary)" />
                  <Loader2 className="animate-spin" size={16} />
               </div>
            )}
            <div ref={scrollRef} />
          </div>
        </div>

        {/* Parsing Loader Overlay - Now fixed relative to the chat area */}
        <AnimatePresence>
          {uploading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{ 
                position: 'absolute', 
                inset: 0, 
                background: 'rgba(var(--bg-rgb), 0.8)', 
                backdropFilter: 'blur(8px)', 
                zIndex: 5, 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                textAlign: 'center',
                padding: '20px'
              }}
            >
              <div style={{ position: 'relative', width: '100px', height: '100px', marginBottom: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  style={{ position: 'absolute', width: '100%', height: '100%', borderRadius: '50%', border: '3px solid rgba(99, 102, 241, 0.1)', borderTopColor: 'var(--primary)' }}
                />
                <FileText size={32} color="var(--primary)" />
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '8px' }}>Parsing Document</h3>
              <p style={{ color: 'var(--text-dim)', fontSize: '14px', maxWidth: '300px', marginBottom: '24px' }}>Extracting intelligence from your file...</p>
              
              <div style={{ background: 'var(--glass)', padding: '8px 20px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid var(--border)' }}>
                 <Loader2 className="animate-spin" size={14} />
                 <span>{logs[logs.length - 1]?.replace(/^\[.*?\]\s*|^\w+:\s*/g, '') || "Preparing..."}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper glass-effect">
          <label style={{ cursor: 'pointer', padding: '12px' }}>
            <input 
              type="file" 
              style={{ display: 'none' }} 
              onChange={handleFileUpload} 
              ref={fileInputRef} 
            />
            <Upload size={20} color={uploading ? "var(--primary)" : "var(--text-dim)"} className={uploading ? "animate-bounce" : ""} />
          </label>
          <input 
            className="input-field" 
            placeholder="Ask anything about your documents..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          />
          <button className="btn-primary" onClick={handleSend} style={{ width: '45px', padding: '0' }} disabled={loading}>
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* Documents Panel (Slide-over) */}
      <AnimatePresence>
        {showDocuments && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowDocuments(false)}
              style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.3)', backdropFilter: 'blur(4px)', zIndex: 10 }}
            />
            <motion.div 
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              style={{ position: 'absolute', top: 0, right: 0, bottom: 0, width: '400px', background: 'var(--bg)', borderLeft: '1px solid var(--border)', zIndex: 11, padding: '32px', boxShadow: '-10px 0 30px rgba(0,0,0,0.1)' }}
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
                  <p>No documents uploaded yet.</p>
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
                        <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{new Date(doc.created_at).toLocaleDateString()} • {doc.file_type || 'Unknown'}</div>
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

const WelcomeState = ({ onUpload, onChat }) => (
  <div style={{ padding: '60px 0', textAlign: 'center' }}>
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div style={{ width: '80px', height: '80px', background: 'var(--glass)', borderRadius: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', border: '1px solid var(--border)' }}>
        <Bot size={40} color="var(--primary)" />
      </div>
      <h2 style={{ fontSize: '32px', fontWeight: '800', marginBottom: '16px' }}>Ready to Explore?</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: '16px', maxWidth: '500px', margin: '0 auto 40px' }}>
        Unlock insights from your data. Upload a document to start precise extraction, or ask a question to begin.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', maxWidth: '600px', margin: '0 auto' }}>
        <div 
          onClick={onUpload}
          className="glass-effect" 
          style={{ padding: '32px', borderRadius: '24px', cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border)', transition: 'transform 0.2s' }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
        >
          <div style={{ padding: '12px', background: '#6366f1', borderRadius: '12px', width: 'fit-content', color: 'white', marginBottom: '16px' }}>
            <Upload size={24} />
          </div>
          <h4 style={{ fontWeight: '700', fontSize: '18px', marginBottom: '8px' }}>Upload New File</h4>
          <p style={{ fontSize: '14px', color: 'var(--text-dim)', margin: 0 }}>Add PDF, TXT, or DOCX files to this session.</p>
        </div>

        <div 
          onClick={onChat}
          className="glass-effect" 
          style={{ padding: '32px', borderRadius: '24px', cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border)', transition: 'transform 0.2s' }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
        >
          <div style={{ padding: '12px', background: '#10b981', borderRadius: '12px', width: 'fit-content', color: 'white', marginBottom: '16px' }}>
            <MessageSquare size={24} />
          </div>
          <h4 style={{ fontWeight: '700', fontSize: '18px', marginBottom: '8px' }}>Chat with Data</h4>
          <p style={{ fontSize: '14px', color: 'var(--text-dim)', margin: 0 }}>Ask questions if data is already available.</p>
        </div>
      </div>
    </motion.div>
  </div>
);

export default ChatWindow;
