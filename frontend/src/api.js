/**
 * api.js — The Backend-Frontend Communication Bridge.
 * 
 * CORE ARCHITECTURE:
 * ─────────────────────────────────────────────────────────────────────────────
 * This module centralizes all HTTP interactions with the FastAPI backend. 
 * By isolating API logic here, we ensure that UI components remain "Dumb" 
 * and pure, focusing only on presentation while this bridge handles data 
 * serialization and endpoint mapping.
 * 
 * WHY THIS APPROACH IS BEST:
 * ──────────────────────────────────────────────────────────────
 * 1. SINGLE SOURCE OF TRUTH: If an endpoint URL changes in the backend, we 
 *    only need to update it here, rather than searching through 50+ components.
 * 2. CONSISTENT HEADERS: Centralizes the handling of 'multipart/form-data' 
 *    and other critical headers for document parsing.
 * 3. SCALABILITY: Easy to inject Axios interceptors for global error handling, 
 *    authentication tokens, or request logging in the future.
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const api = {
  // Session management
  getSessions: () => axios.get(`${API_BASE_URL}/sessions`),
  createSession: (id, title) => axios.post(`${API_BASE_URL}/sessions`, { id, title }),
  deleteSession: (id) => axios.delete(`${API_BASE_URL}/sessions/${id}`),
  
  // Chat messages
  getMessages: (sessionId) => axios.get(`${API_BASE_URL}/sessions/${sessionId}/messages`),
  sendMessage: (sessionId, role, content) => axios.post(`${API_BASE_URL}/sessions/${sessionId}/messages`, { role, content }),
  askQuestion: (sessionId, content, model = null) => axios.post(`${API_BASE_URL}/sessions/${sessionId}/ask`, { role: 'user', content, model }),
  getDocuments: (sessionId) => axios.get(`${API_BASE_URL}/sessions/${sessionId}/documents`),
  
  // Feedback
  submitFeedback: (messageId, isPositive, comment) => axios.post(`${API_BASE_URL}/feedback`, { message_id: messageId, is_positive: isPositive, comment }),
  
  // Parsing & Chunking
  parseDocument: (formData) => axios.post(`${API_BASE_URL}/parse`, formData),
  // session_id is critical — it sets the ChromaDB collection name so the chat window can retrieve vectors
  chunkDocument: (docId, config) => axios.post(`${API_BASE_URL}/chunk/${docId}`, config),
  getChunks: (docId) => axios.get(`${API_BASE_URL}/documents/${docId}/chunks`),

  // Stats
  getSystemStats: () => axios.get(`${API_BASE_URL}/system/stats`),

  // Ollama — fetch locally available models via backend proxy (avoids CORS)
  getOllamaModels: () => axios.get(`${API_BASE_URL}/ollama/models`),
};

export const WS_URL = 'ws://localhost:8000/ws/logs';
