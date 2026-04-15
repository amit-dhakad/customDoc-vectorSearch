/**
 * AdvancedParsing.jsx — The Professional Intelligence Orchestration Wizard.
 * 
 * CORE COMPONENT PHILOSOPHY:
 * ─────────────────────────────────────────────────────────────────────────────
 * This component is designed to provide transparency and expert-level control 
 * over the document ingestion process. In standard RAG systems, parsing is a 
 * "black box." Here, we break it into 5 distinct, observable steps.
 * 
 * THE 5-STEP INTELLIGENCE PIPELINE:
 * ──────────────────────────────────────────────────────────────
 * 1. EXTRACTION CONFIG: User chooses the engine (Fitz vs pdfplumber vs OCR).
 * 2. LIVE ANALYSIS: Real-time logs stream via WebSockets.
 * 3. CHUNKING STRATEGY: user chooses how to "slice" knowledge.
 * 4. VECTOR SELECTION: User chooses the mathematical "retrieval bridge."
 * 5. INTELLIGENCE GALLERY: A visual preview of the final searchable fragments.
 * 
 * KEY FIX: A session_id is generated on mount and threaded through the entire
 * pipeline so parsed document vectors land in the SAME ChromaDB collection
 * that the destination chat window will query.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Upload, Settings, FileText, ChevronRight, Loader2, Play, CheckCircle, MessageSquare, X, AlertCircle, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { api, WS_URL } from '../api';

const AdvancedParsing = () => {
  const [file, setFile] = useState(null);
  const [engine, setEngine] = useState('fitz');
  const [useOcr, setUseOcr] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [step, setStep] = useState(1); // 1: Config, 2: Parsing, 3: Chunking, 4: Vectors, 5: Preview
  const [chunkMethod, setChunkMethod] = useState('recursive');
  const [vectorMethod, setVectorMethod] = useState('hybrid');
  const [chunks, setChunks] = useState([]);
  const [chunking, setChunking] = useState(false);
  const [serverMethod, setServerMethod] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // ── Session ─────────────────────────────────────────────────────────────
  // Generate a stable session_id on mount. This is threaded through ALL pipeline
  // steps so document, vectors, and chat all share the same identifier.
  const sessionId = useRef(Math.random().toString(36).substring(2, 10)).current;

  // ── WebSocket ────────────────────────────────────────────────────────────
  const ws = useRef(null);
  const clientId = useRef(Math.random().toString(36).substring(7)).current;

  useEffect(() => {
    ws.current = new WebSocket(`${WS_URL}/${clientId}`);
    ws.current.onmessage = (event) => {
      setLogs(prev => [...prev, event.data]);
    };
    return () => ws.current?.close();
  }, [clientId]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const resetPipeline = () => {
    setStep(1);
    setFile(null);
    setResult(null);
    setChunks([]);
    setLogs([]);
    setError(null);
  };

  // ── Step 1 → 2: Parse ────────────────────────────────────────────────────
  const startParsing = async () => {
    if (!file) return;
    setParsing(true);
    setStep(2);
    setError(null);
    setLogs(['Initializing parsing pipeline…']);

    // Create the session in DB first so documents can be linked
    try {
      await api.createSession(sessionId, `Doc: ${file.name}`);
    } catch (_) { /* session may already exist */ }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', engine);
    formData.append('ocr', useOcr.toString());
    formData.append('client_id', clientId);
    formData.append('session_id', sessionId);  // ← KEY: links document to session in DB

    try {
      const res = await api.parseDocument(formData);
      setResult(res.data);
      setStep(3);
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message;
      setLogs(prev => [...prev, `ERROR: ${errMsg}`]);
      setError(errMsg);
    } finally {
      setParsing(false);
    }
  };

  // ── Step 4 → 5: Chunk + Vectorize ───────────────────────────────────────
  const startChunking = async () => {
    if (!result || !result.text) return;
    setChunking(true);
    setError(null);
    setLogs(prev => [...prev, `Applying ${chunkMethod.toUpperCase()} segmentation…`]);

    const chunkConfig = {
      method: chunkMethod,
      vector_method: vectorMethod,
      client_id: clientId,
      text: result.text,
      session_id: sessionId,  // ← KEY: vectors stored in this session's ChromaDB collection
    };

    try {
      const res = await api.chunkDocument(result.doc_id || 'demo', chunkConfig);
      setChunks(res.data.chunks || []);
      setServerMethod(res.data.vector_method);
      setStep(5);
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message;
      setLogs(prev => [...prev, `ERROR: ${errMsg}`]);
      setError(errMsg);
    } finally {
      setChunking(false);
    }
  };

  const getLatestStatus = () => {
    if (logs.length === 0) return 'Preparing engine…';
    const lastLog = logs[logs.length - 1];
    return lastLog.replace(/^\[.*?\]\s*|^\w+:\s*/g, '');
  };

  // ── Navigate to the linked chat session ──────────────────────────────────
  const handleStartChatting = () => {
    navigate(`/chat/${sessionId}`);
  };

  return (
    <div style={{ flex: 1, padding: '40px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', background: 'var(--primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Settings size={24} color="white" />
          </div>
          <div>
            <h2 style={{ fontSize: '24px', fontWeight: '700' }}>Advanced Document Pipeline</h2>
            <p style={{ color: 'var(--text-dim)' }}>Fine-tune extraction parameters and observe real-time parsing.</p>
          </div>
        </div>
      </div>

      {/* Error banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginBottom: '24px', overflow: 'hidden' }}
          >
            <div style={{
              padding: '16px 20px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--error)',
              borderRadius: '12px',
              color: 'var(--error)',
              fontSize: '14px',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <AlertCircle size={18} />
              <div style={{ flex: 1 }}>{error}</div>
              <button onClick={() => setError(null)} style={{ background: 'transparent', border: 'none', color: 'var(--error)', cursor: 'pointer' }}>
                <X size={16} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress steps */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '40px', flexWrap: 'wrap' }}>
        {[1, 2, 3, 4, 5].map(s => (
          <div key={s} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: step >= s ? 1 : 0.3,
            color: step === s ? 'var(--primary)' : 'inherit'
          }}>
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: step > s ? '#10b981' : step === s ? 'var(--primary)' : 'var(--glass)',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {step > s ? <CheckCircle size={14} /> : s}
            </div>
            <span style={{ fontSize: '13px', fontWeight: '500' }}>
              {s === 1 ? 'Extraction' : s === 2 ? 'Analysis' : s === 3 ? 'Chunking' : s === 4 ? 'Vectors' : 'Intelligence'}
            </span>
            {s < 5 && <ChevronRight size={16} />}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* ── Step 1: Config ── */}
        {step === 1 && (
          <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
            <div className="glass-effect" style={{ padding: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', color: 'var(--text-dim)', marginBottom: '12px' }}>Engine Selection</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {[
                    { id: 'fitz', name: 'PyMuPDF (fitz)', desc: 'Fast, efficient layout-heavy documents. Best for general purpose.' },
                    { id: 'pdfplumber', name: 'pdfplumber', desc: 'High accuracy for tables and complex structures. Slower than fitz.' },
                  ].map(e => (
                    <div
                      key={e.id}
                      onClick={() => setEngine(e.id)}
                      style={{
                        padding: '16px',
                        borderRadius: '12px',
                        background: engine === e.id ? 'var(--glass)' : 'transparent',
                        border: `1px solid ${engine === e.id ? 'var(--primary)' : 'var(--border)'}`,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ fontWeight: '600', marginBottom: '4px' }}>{e.name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{e.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '32px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                  <div
                    onClick={() => setUseOcr(!useOcr)}
                    style={{
                      width: '40px', height: '20px',
                      background: useOcr ? 'var(--primary)' : 'var(--glass)',
                      borderRadius: '20px', position: 'relative',
                      border: '1px solid var(--border)', transition: 'all 0.3s'
                    }}
                  >
                    <div style={{
                      width: '16px', height: '16px', background: 'white', borderRadius: '50%',
                      position: 'absolute', top: '1px',
                      left: useOcr ? '21px' : '2px', transition: 'all 0.3s'
                    }} />
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '14px' }}>Force OCR Mode</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Use Tesseract CPU engine to extract text from scanned images.</div>
                  </div>
                </label>
              </div>

              <div style={{ marginBottom: '32px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', color: 'var(--text-dim)', marginBottom: '12px' }}>Upload Document</label>
                <label style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  padding: '40px', border: '2px dashed var(--border)', borderRadius: '16px', cursor: 'pointer',
                  background: file ? 'rgba(99, 102, 241, 0.05)' : 'transparent', transition: 'all 0.2s',
                }}>
                  <input type="file" style={{ display: 'none' }} onChange={handleFileChange} />
                  <Upload size={32} color={file ? 'var(--primary)' : 'var(--text-dim)'} style={{ marginBottom: '12px' }} />
                  <span style={{ fontWeight: '500' }}>{file ? file.name : 'Drop file here or click to browse'}</span>
                  {file && <span style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>{(file.size / 1024).toFixed(1)} KB</span>}
                </label>
              </div>

              <button className="btn-primary" onClick={startParsing} disabled={!file} style={{ width: '100%', padding: '16px' }}>
                Initialize Extraction <Play size={18} fill="currentColor" />
              </button>
            </div>
          </motion.div>
        )}

        {/* ── Step 2: Parsing / Live Analysis ── */}
        {step === 2 && (
          <motion.div
            key="step2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 20px', textAlign: 'center' }}
          >
            {/* Multi-ring spinner */}
            <div style={{ position: 'relative', width: '120px', height: '120px', marginBottom: '40px' }}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                style={{
                  position: 'absolute', inset: 0, borderRadius: '50%',
                  border: '3px solid transparent',
                  borderTopColor: 'var(--primary)', borderRightColor: 'rgba(99,102,241,0.25)',
                }}
              />
              <motion.div
                animate={{ rotate: -360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
                style={{
                  position: 'absolute', inset: '14px', borderRadius: '50%',
                  border: '2px solid transparent',
                  borderTopColor: '#10b981', borderLeftColor: 'rgba(16,185,129,0.25)',
                }}
              />
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 1.5, repeat: Infinity }}>
                  <FileText size={28} color="var(--primary)" />
                </motion.div>
              </div>
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: '800', marginBottom: '12px', color: error ? 'var(--error)' : 'inherit' }}>
              {error ? 'Extraction Failed' : 'Processing Your Document'}
            </h3>
            <p style={{ color: 'var(--text-dim)', maxWidth: '400px', fontSize: '16px', marginBottom: '24px' }}>
              Our intelligence engine is currently analyzing "{file?.name}" to extract consistent text and structure.
            </p>

            <motion.div
              key={error ? 'error' : getLatestStatus()}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                background: error ? 'rgba(239, 68, 68, 0.1)' : 'var(--glass)',
                padding: '12px 24px', borderRadius: '30px', fontSize: '14px', fontWeight: '600',
                color: error ? 'var(--error)' : 'var(--primary)',
                display: 'flex', alignItems: 'center', gap: '10px',
                border: `1px solid ${error ? 'var(--error)' : 'var(--border)'}`,
                maxWidth: '400px',
              }}
            >
              {!error && (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                  style={{ width: '14px', height: '14px', borderRadius: '50%', border: '2px solid var(--primary)', borderTopColor: 'transparent', flexShrink: 0 }}
                />
              )}
              {error && <AlertCircle size={16} />}
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {error ? 'Pipeline Halted' : getLatestStatus()}
              </span>
            </motion.div>

            {error && (
              <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={resetPipeline}
                className="btn-primary"
                style={{ marginTop: '32px', background: 'var(--glass)', border: '1px solid var(--border)', color: 'var(--text-main)' }}
              >
                <RotateCcw size={18} /> Back to Configuration
              </motion.button>
            )}
          </motion.div>
        )}

        {/* ── Step 3: Chunking Strategy ── */}
        {step === 3 && (
          <motion.div key="step3" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}>
            <div className="glass-effect" style={{ padding: '40px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div className="success-badge">
                  <CheckCircle size={18} /> Extraction Complete
                </div>
              </div>

              <div style={{ textAlign: 'left', marginBottom: '40px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '16px' }}>Step 3: Select Chunking Strategy</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '14px', marginBottom: '24px' }}>
                  Choose how to segment the text for semantic indexing.
                </p>

                {result && result.text && (
                  <div style={{ marginBottom: '32px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
                      Extraction Preview
                    </label>
                    <div className="glass-effect" style={{
                      padding: '20px',
                      background: 'rgba(0,0,0,0.2)',
                      maxHeight: '300px',
                      overflowY: 'auto',
                      fontSize: '13px',
                      lineHeight: '1.6',
                      fontFamily: 'JetBrains Mono, monospace',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      whiteSpace: 'pre-wrap',
                      color: 'var(--text-dim)',
                    }}>
                      {result.text.substring(0, 2000)}{result.text.length > 2000 ? '\n\n… (truncated for preview)' : ''}
                    </div>
                    <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-dim)' }}>
                      ✓ {result.text.length.toLocaleString()} characters extracted
                    </div>
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '32px' }}>
                  {[
                    { id: 'fixed', name: 'Fixed Size', desc: 'Predictable slices.' },
                    { id: 'overlap', name: 'Fixed Overlap', desc: 'Preserves edge context.' },
                    { id: 'recursive', name: 'Recursive', desc: 'Smarter paragraph cuts.' },
                    { id: 'structural', name: 'Structural', desc: 'Markdown header aware.' },
                    { id: 'semantic', name: 'Semantic', desc: 'Context shift detection.' }
                  ].map(m => (
                    <div
                      key={m.id}
                      onClick={() => setChunkMethod(m.id)}
                      className={`card-interactive ${chunkMethod === m.id ? 'active' : ''}`}
                      style={{
                        padding: '16px',
                        borderColor: chunkMethod === m.id ? 'var(--primary)' : 'var(--border)',
                        background: chunkMethod === m.id ? 'var(--glass)' : 'transparent',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ fontWeight: '700', fontSize: '15px', marginBottom: '4px' }}>{m.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', lineHeight: '1.4' }}>{m.desc}</div>
                    </div>
                  ))}
                </div>

                <button
                  className="btn-primary"
                  onClick={() => setStep(4)}
                  style={{ width: '100%', padding: '16px' }}
                >
                  Continue to Vectorization
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── Step 4: Vector Strategy ── */}
        {step === 4 && !chunking && (
          <motion.div key="step4" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
            <div className="glass-effect" style={{ padding: '40px' }}>
              <div style={{ textAlign: 'left', marginBottom: '40px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '16px' }}>Step 4: Vector Strategy</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '14px', marginBottom: '24px' }}>
                  Choose the embedding method for search retrieval.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '32px' }}>
                  {[
                    { id: 'dense', name: 'Dense', desc: 'MiniLM-L6 (Semantic)' },
                    { id: 'sparse', name: 'Sparse', desc: 'BM25 (Exact Keywords)' },
                    { id: 'hybrid', name: 'Hybrid', desc: 'Dense + Sparse (Best)' },
                    { id: 'colbert', name: 'ColBERT', desc: 'Late Interaction (Accurate)' }
                  ].map(m => (
                    <div
                      key={m.id}
                      onClick={() => setVectorMethod(m.id)}
                      className={`card-interactive ${vectorMethod === m.id ? 'active' : ''}`}
                      style={{
                        padding: '16px',
                        borderColor: vectorMethod === m.id ? 'var(--primary)' : 'var(--border)',
                        background: vectorMethod === m.id ? 'var(--glass)' : 'transparent',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ fontWeight: '700', fontSize: '15px', marginBottom: '4px' }}>{m.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', lineHeight: '1.4' }}>{m.desc}</div>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button onClick={() => setStep(3)} style={{ flex: 1, padding: '16px', background: 'var(--glass)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text)', cursor: 'pointer' }}>
                    Back
                  </button>
                  <button className="btn-primary" onClick={startChunking} style={{ flex: 2, padding: '16px' }}>
                    Process Intelligence Chunks
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── Chunking overlay (shown over step 4 while chunking) ── */}
        {chunking && (
          <motion.div
            key="chunking-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed', inset: 0,
              background: 'rgba(var(--bg-rgb), 0.9)',
              backdropFilter: 'blur(16px)',
              zIndex: 100,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              textAlign: 'center', gap: '24px',
            }}
          >
            <div style={{ position: 'relative', width: '110px', height: '110px' }}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '3px solid transparent', borderTopColor: 'var(--primary)', borderRightColor: 'rgba(99,102,241,0.25)' }}
              />
              <motion.div
                animate={{ rotate: -360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
                style={{ position: 'absolute', inset: '14px', borderRadius: '50%', border: '2px solid transparent', borderTopColor: '#10b981', borderLeftColor: 'rgba(16,185,129,0.25)' }}
              />
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 1.4, repeat: Infinity }}>
                  <Settings size={28} color="var(--primary)" />
                </motion.div>
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '10px' }}>Building Intelligence</h3>
              <p style={{ color: 'var(--text-dim)', fontSize: '14px', maxWidth: '360px' }}>
                Applying <strong style={{ color: 'var(--primary)' }}>{chunkMethod}</strong> segmentation
                and indexing vectors into your document workspace…
              </p>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              {[0, 1, 2].map(i => (
                <motion.div
                  key={i}
                  animate={{ y: [0, -10, 0], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.2, ease: 'easeInOut' }}
                  style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--primary)' }}
                />
              ))}
            </div>

            <motion.div
              key={logs[logs.length - 1] || 'chunk-init'}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                background: 'var(--glass)', padding: '8px 20px', borderRadius: '20px',
                fontSize: '12px', fontWeight: '600', color: 'var(--primary)',
                border: '1px solid var(--border)', maxWidth: '340px',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {logs[logs.length - 1]?.replace(/^\[.*?\]\s*|^\w+:\s*/g, '') || 'Segmenting…'}
            </motion.div>
          </motion.div>
        )}

        {/* ── Step 5: Intelligence Gallery ── */}
        {step === 5 && (
          <motion.div key="step5" initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }}>
            <div className="glass-effect" style={{ padding: '40px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '24px', fontWeight: '800' }}>Intelligence Gallery</h3>
                  <p style={{ color: 'var(--text-dim)', fontSize: '14px' }}>
                    Generated <strong>{chunks.length}</strong> fragments using
                    <strong> {chunkMethod}</strong> + <strong>{serverMethod || vectorMethod}</strong>.
                    Your document is ready to chat.
                  </p>
                </div>
                <button className="btn-primary" onClick={handleStartChatting} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <MessageSquare size={18} /> Chat with this Document
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px', maxHeight: '500px', overflowY: 'auto', padding: '10px' }}>
                {chunks.map((c, i) => (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.04, 0.5) }}
                    key={i}
                    className="glass-effect"
                    style={{ padding: '20px', borderRadius: '16px', textAlign: 'left', border: '1px solid var(--border)', background: 'var(--bg-card)' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                      <span style={{ fontSize: '10px', fontWeight: '800', color: 'var(--primary)', textTransform: 'uppercase' }}>Fragment #{i + 1}</span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{c.length} chars</span>
                    </div>
                    <div style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text)', maxHeight: '120px', overflowY: 'hidden', maskImage: 'linear-gradient(to bottom, black 70%, transparent 100%)' }}>
                      {c}
                    </div>
                  </motion.div>
                ))}
              </div>

              <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button
                  onClick={() => setStep(4)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '14px', fontWeight: '600' }}
                >
                  Adjust Vector Settings
                </button>
                <button
                  onClick={resetPipeline}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <RotateCcw size={14} /> Parse Another Document
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AdvancedParsing;
