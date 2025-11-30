const { Client, GatewayIntentBits } = require('discord.js');
const { BOT_TOKEN } = require('../config/env');
const logger = require('../utils/logger');

let client = null;

const initDiscordBot = () => {
  if (!BOT_TOKEN) {
    logger.warn('No BOT_TOKEN provided. Discord bot will not start.');
    return;
  }

  client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages] });

  client.once('ready', () => {
    logger.info(`✅ Discord bot logged in as ${client.user.tag}`);
  });

  client.login(BOT_TOKEN).catch(error => {
    logger.error('❌ Failed to login Discord bot:', error.message);
  });
};

module.exports = {
  initDiscordBot,
  getClient: () => client
};
