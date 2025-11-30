const logger = require('../utils/logger');

exports.requestLogger = (req, res, next) => {
  logger.info(`${req.method} ${req.url}`);
  next();
};
