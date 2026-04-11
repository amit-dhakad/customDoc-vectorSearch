import React, { useState, useEffect, useRef } from 'react';
import { Upload, Settings, FileText, ChevronRight, Loader2, Play, Home, CheckCircle, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { api, WS_URL } from '../api';

const AdvancedParsing = () => {
  const [file, setFile] = useState(null);
  const [engine, setEngine] = useState('fitz');
  const [useOcr, setUseOcr] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [step, setStep] = useState(1); // 1: Upload, 2: Parsing Loader, 3: Result
  const navigate = useNavigate();
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
  };

  const startParsing = async () => {
    if (!file) return;
    setParsing(true);
    setStep(2);
    setLogs(["Initializing parsing pipeline..."]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', engine);
    formData.append('ocr', useOcr.toString());
    formData.append('client_id', clientId);

    try {
      const res = await api.parseDocument(formData);
      setResult(res.data);
      setStep(3);
    } catch (err) {
      setLogs(prev => [...prev, `ERROR: ${err.response?.data?.detail || err.message}`]);
    } finally {
      setParsing(false);
    }
  };

  const getLatestStatus = () => {
    if (logs.length === 0) return "Preparing engine...";
    const lastLog = logs[logs.length - 1];
    // Strip technical prefixes if they exist (like [INFO], DEBUG:, etc)
    return lastLog.replace(/^\[.*?\]\s*|^\w+:\s*/g, '');
  };

  return (
    <div style={{ flex: 1, padding: '40px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
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

      <div style={{ display: 'flex', gap: '8px', marginBottom: '40px' }}>
         {[1, 2, 3].map(s => (
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
                 background: step >= s ? 'var(--primary)' : 'var(--glass)',
                 color: 'white',
                 display: 'flex',
                 alignItems: 'center',
                 justifyContent: 'center',
                 fontSize: '12px',
                 fontWeight: 'bold'
                }}>
                   {s}
               </div>
               <span style={{ fontSize: '14px', fontWeight: '500' }}>
                  {s === 1 ? 'Configure' : s === 2 ? 'Analysis' : 'Extracted Text'}
               </span>
               {s < 3 && <ChevronRight size={16} />}
            </div>
         ))}
      </div>

      <AnimatePresence mode="wait">
        {step === 1 && (
          <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
            <div className="glass-effect" style={{ padding: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', color: 'var(--text-dim)', marginBottom: '12px' }}>Engine Selection</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div 
                    onClick={() => setEngine('fitz')}
                    style={{ 
                      padding: '16px', 
                      borderRadius: '12px', 
                      background: engine === 'fitz' ? 'var(--glass)' : 'transparent',
                      border: `1px solid ${engine === 'fitz' ? 'var(--primary)' : 'var(--border)'}`,
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontWeight: '600', marginBottom: '4px' }}>PyMuPDF (fitz)</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Fast, efficient layout-heavy documents. Best for general purpose.</div>
                  </div>
                  <div 
                    onClick={() => setEngine('pdfplumber')}
                    style={{ 
                      padding: '16px', 
                      borderRadius: '12px', 
                      background: engine === 'pdfplumber' ? 'var(--glass)' : 'transparent',
                      border: `1px solid ${engine === 'pdfplumber' ? 'var(--primary)' : 'var(--border)'}`,
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontWeight: '600', marginBottom: '4px' }}>pdfplumber</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>High accuracy for tables and complex structures. Slower than fitz.</div>
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '32px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                  <div 
                    onClick={() => setUseOcr(!useOcr)}
                    style={{ 
                      width: '40px', 
                      height: '20px', 
                      background: useOcr ? 'var(--primary)' : 'var(--glass)', 
                      borderRadius: '20px', 
                      position: 'relative',
                      border: '1px solid var(--border)',
                      transition: 'all 0.3s'
                    }}
                  >
                    <div style={{ 
                      width: '16px', 
                      height: '16px', 
                      background: 'white', 
                      borderRadius: '50%', 
                      position: 'absolute',
                      top: '1px',
                      left: useOcr ? '21px' : '2px',
                      transition: 'all 0.3s'
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
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  padding: '40px', 
                  border: '2px dashed var(--border)', 
                  borderRadius: '16px', 
                  cursor: 'pointer',
                  background: file ? 'rgba(99, 102, 241, 0.05)' : 'transparent'
                }}>
                  <input type="file" style={{ display: 'none' }} onChange={handleFileChange} />
                  <Upload size={32} color={file ? 'var(--primary)' : 'var(--text-dim)'} style={{ marginBottom: '12px' }} />
                  <span style={{ fontWeight: '500' }}>{file ? file.name : 'Drop file here or click to browse'}</span>
                </label>
              </div>

              <button className="btn-primary" onClick={startParsing} disabled={!file} style={{ width: '100%', padding: '16px' }}>
                Initialize Extraction <Play size={18} fill="currentColor" />
              </button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div 
            key="step2" 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0, y: -20 }}
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center', 
              padding: '60px 20px',
              textAlign: 'center'
            }}
          >
            <div style={{ 
              position: 'relative', 
              width: '120px', 
              height: '120px', 
              marginBottom: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                style={{ 
                  position: 'absolute',
                  width: '100%', 
                  height: '100%', 
                  borderRadius: '50%', 
                  border: '3px solid rgba(99, 102, 241, 0.1)',
                  borderTopColor: 'var(--primary)',
                  boxShadow: '0 0 15px rgba(99, 102, 241, 0.1)'
                }}
              />
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                style={{ 
                  background: 'var(--glass)',
                  padding: '14px',
                  borderRadius: '16px',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
                }}
              >
                <FileText size={28} color="var(--primary)" />
              </motion.div>
            </div>
            
            <h3 style={{ fontSize: '24px', fontWeight: '800', marginBottom: '12px' }}>
              Processing Your Document
            </h3>
            <p style={{ color: 'var(--text-dim)', maxWidth: '400px', fontSize: '16px', marginBottom: '24px' }}>
              Our intelligence engine is currently analyzing "{file?.name}" to extract consistent text and structure.
            </p>

            <div style={{ 
              background: 'var(--glass)', 
              padding: '12px 24px', 
              borderRadius: '30px', 
              fontSize: '14px', 
              fontWeight: '600',
              color: 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              border: '1px solid var(--border)'
            }}>
              <Loader2 className="animate-spin" size={16} />
              <AnimatePresence mode="wait">
                <motion.span
                  key={getLatestStatus()}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                >
                  {getLatestStatus()}
                </motion.span>
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div key="step3" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}>
            <div className="glass-effect" style={{ padding: '48px 32px', textAlign: 'center' }}>
              <div className="success-badge">
                 <CheckCircle size={18} /> Documentation Parsed Successfully
              </div>
              
              <h2 style={{ fontSize: '32px', fontWeight: '800', marginBottom: '16px' }}>Analysis Complete!</h2>
              <p style={{ color: 'var(--text-dim)', fontSize: '16px', maxWidth: '500px', margin: '0 auto 40px' }}>
                Your data has been processed and is ready for exploration. What would you like to do next?
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', maxWidth: '700px', margin: '0 auto 40px' }}>
                <div 
                  className="card-interactive"
                  onClick={() => setStep(1)}
                >
                  <div style={{ padding: '12px', background: 'var(--glass)', borderRadius: '12px', width: 'fit-content', color: 'var(--text-dim)', marginBottom: '16px', border: '1px solid var(--border)' }}>
                    <Upload size={24} />
                  </div>
                  <h4 style={{ fontWeight: '700', fontSize: '18px', marginBottom: '8px' }}>Upload New File</h4>
                  <p style={{ fontSize: '14px', color: 'var(--text-dim)', margin: 0 }}>Process another document with fine-tuned parameters.</p>
                </div>

                <div 
                  className="card-interactive"
                  onClick={() => {
                    const id = Math.random().toString(36).substring(7);
                    navigate(`/chat/${id}`);
                  }}
                  style={{ borderColor: 'var(--primary)' }}
                >
                  <div style={{ padding: '12px', background: 'var(--primary)', borderRadius: '12px', width: 'fit-content', color: 'white', marginBottom: '16px' }}>
                    <MessageSquare size={24} />
                  </div>
                  <h4 style={{ fontWeight: '700', fontSize: '18px', marginBottom: '8px' }}>Chat with Data</h4>
                  <p style={{ fontSize: '14px', color: 'var(--text-dim)', margin: 0 }}>Start a new conversation session using this extracted data.</p>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '32px', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-dim)' }}>Extraction Preview</h3>
                  <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{result?.engine_used} Engine</div>
                </div>
                
                <div style={{ 
                  background: 'rgba(0,0,0,0.2)', 
                  padding: '20px', 
                  borderRadius: '12px', 
                  maxHeight: '200px', 
                  overflowY: 'auto',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  color: 'var(--text-dim)',
                  border: '1px solid var(--border)',
                  textAlign: 'left'
                }}>
                  {result?.text || "No text extracted."}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AdvancedParsing;
