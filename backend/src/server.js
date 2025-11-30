const app = require('./app');
const { PORT } = require('./config/env');
const logger = require('./utils/logger');
const { initDiscordBot } = require('./services/discordService');
const sequelize = require('./config/database');

const authRoutes = require('./routes/authRoutes');
const apiRoutes = require('./routes/apiRoutes');
const noteRoutes = require('./routes/noteRoutes');
const { errorHandler } = require('./middleware/errorHandler');
const { requestLogger } = require('./middleware/requestLogger');

// Start Discord Bot
initDiscordBot();

// Middleware
app.use(requestLogger);

// Routes
app.use('/auth', authRoutes);
app.use('/api', apiRoutes);
app.use('/api/notes', noteRoutes);

// Error handling middleware
app.use(errorHandler);

// Sync Database and Start Server
sequelize.sync().then(() => {
  logger.info('Database synced');
  app.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
  });
}).catch(err => {
  logger.error('Failed to sync database:', err);
});
