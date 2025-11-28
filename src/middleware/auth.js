const crypto = require('crypto');
const { SESSION_SECRET } = require('../config/env');

// Simple in-memory session store (as per requirements to keep it simple/node.js)
// In a real production app, use Redis or a database-backed store
const sessions = new Map();

const generateSessionToken = () => {
  return crypto.randomBytes(32).toString('hex');
};

const createSession = (user) => {
  const token = generateSessionToken();
  const sessionData = {
    userId: user.id,
    username: user.username,
    email: user.email,
    createdAt: new Date().toISOString(),
    lastAccessed: new Date().toISOString()
  };
  sessions.set(token, sessionData);
  return token;
};

const getSession = (token) => {
  if (!token) return null;
  const session = sessions.get(token);
  if (session) {
    // Update last accessed time
    session.lastAccessed = new Date().toISOString();
    sessions.set(token, session);
  }
  return session;
};

const deleteSession = (token) => {
  if (token) {
    sessions.delete(token);
  }
};

const requireAuth = (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const session = getSession(token);
  
  if (!session) {
    return res.status(401).json({
      success: false,
      message: 'Authentication required',
      requiresAuth: true
    });
  }
  
  req.user = session;
  next();
};

module.exports = {
  createSession,
  getSession,
  deleteSession,
  requireAuth
};
