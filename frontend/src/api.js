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
  getDocuments: (sessionId) => axios.get(`${API_BASE_URL}/sessions/${sessionId}/documents`),
  
  // Feedback
  submitFeedback: (messageId, isPositive, comment) => axios.post(`${API_BASE_URL}/feedback`, { message_id: messageId, is_positive: isPositive, comment }),
  
  // Parsing
  parseDocument: (formData) => axios.post(`${API_BASE_URL}/parse`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  
  // Stats
  getSystemStats: () => axios.get(`${API_BASE_URL}/system/stats`)
};

export const WS_URL = 'ws://localhost:8000/ws/logs';
