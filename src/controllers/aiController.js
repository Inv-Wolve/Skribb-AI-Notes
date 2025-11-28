const axios = require('axios');
const { AI_API_KEY, AI_CODER_API_KEY, FRONTEND_URL, IS_PRODUCTION, IS_DEVELOPMENT } = require('../config/env');
const logger = require('../utils/logger');

// Helper to call OpenRouter API
async function callOpenRouterAPI(prompt, userText, apiKey, model) {
  if (!apiKey) {
    throw new Error('API Key not found');
  }

  const response = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
    model: model,
    messages: [
      { role: 'system', content: prompt },
      { role: 'user', content: userText }
    ],
    temperature: 0.3,
    max_tokens: 2000
  }, {
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': FRONTEND_URL,
      'X-Title': 'AI Enhancement Server'
    }
  });

  if (!response.data.choices || !response.data.choices[0] || !response.data.choices[0].message) {
    throw new Error('Invalid response format from OpenRouter API');
  }

  return response.data.choices[0].message.content;
}

exports.enhanceText = async (req, res, next) => {
  try {
    const { text } = req.body;

    const enhancePrompt = `You are a professional text editor. Your task is to enhance the provided text by:
1. Correcting grammar and spelling errors
2. Improving clarity and flow
3. Summarizing if the text is too verbose (while keeping key information)
4. Making it more professional and readable
5. Maintaining the original meaning and intent

Please return only the enhanced text without any additional commentary or explanations.`;

    if (IS_DEVELOPMENT) {
      logger.debug('Enhancing text:', text.substring(0, 100) + '...');
    }
    
    const enhancedText = await callOpenRouterAPI(enhancePrompt, text, AI_API_KEY, 'deepseek/deepseek-chat-v3.1:free');

    res.json({
      success: true,
      enhancedText: enhancedText.trim()
    });

  } catch (error) {
    logger.error('Error in /txt-enhance:', error.message);
    if (error.message.includes('API Key')) {
      return res.status(500).json({ success: false, error: 'Server configuration error: Missing API key' });
    }
    next(error);
  }
};

exports.fixText = async (req, res, next) => {
  try {
    const { text } = req.body;

    const fixPrompt = `You are a grammar and spelling checker. Your task is to:
1. Correct grammar and spelling errors ONLY
2. Do NOT change the meaning, tone, or style of the text
3. Do NOT summarize or rephrase the content
4. Keep the original structure and formatting as much as possible
5. Only make minimal necessary corrections

Please return only the corrected text without any additional commentary or explanations.`;

    if (IS_DEVELOPMENT) {
      logger.debug('Fixing text:', text.substring(0, 100) + '...');
    }
    
    const fixedText = await callOpenRouterAPI(fixPrompt, text, AI_API_KEY, 'deepseek/deepseek-chat-v3.1:free');

    res.json({
      success: true,
      fixedText: fixedText.trim()
    });

  } catch (error) {
    logger.error('Error in /txt-fix:', error.message);
    if (error.message.includes('API Key')) {
      return res.status(500).json({ success: false, error: 'Server configuration error: Missing API key' });
    }
    next(error);
  }
};

exports.enhanceCode = async (req, res, next) => {
  try {
    const { code, language } = req.body;
    const langContext = language ? ` The code is written in ${language}.` : '';

    const codeEnhancePrompt = `You are a senior software engineer and code reviewer. Your task is to enhance the provided code by:
1. Adding comprehensive documentation (docstrings, comments)
2. Improving code structure and formatting
3. Following best practices and conventions for the language
4. Adding type hints where applicable
5. Improving variable and function names for clarity
6. Adding error handling where appropriate
7. Optimizing for readability and maintainability
8. Adding example usage if it's a function or class

${langContext}

Please return only the enhanced code with improvements. Do not include explanations or commentary outside of code comments.`;

    if (IS_DEVELOPMENT) {
      logger.debug('Enhancing code:', code.substring(0, 150) + '...');
    }
    
    const enhancedCode = await callOpenRouterAPI(codeEnhancePrompt, code, AI_CODER_API_KEY, 'qwen/qwen-2.5-coder:free');

    res.json({
      success: true,
      enhancedCode: enhancedCode.trim(),
      language: language || 'auto-detected'
    });

  } catch (error) {
    logger.error('Error in /code-enhance:', error.message);
    if (error.message.includes('API Key')) {
      return res.status(500).json({ success: false, error: 'Server configuration error: Missing Code API key' });
    }
    next(error);
  }
};
