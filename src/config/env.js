const path = require('path');
require('dotenv').config();

const NODE_ENV = process.env.NODE_ENV || 'development';

module.exports = {
  NODE_ENV,
  IS_PRODUCTION: NODE_ENV === 'production',
  IS_DEVELOPMENT: NODE_ENV === 'development',
  PORT: process.env.PORT || 5500,
  USERS_FILE: path.join(__dirname, '../../users.json'),
  SALT_ROUNDS: 12,
  AI_API_KEY: process.env.AI_API_KEY,
  AI_CODER_API_KEY: process.env.AI_CODER_API_KEY,
  BOT_TOKEN: process.env.BOT_TOKEN,
  FRONTEND_URL: process.env.FRONTEND_URL || 'https://zykro.dev',
  SESSION_SECRET: process.env.SESSION_SECRET || 'default_secret_key_change_in_prod'
};
