const fs = require('fs');
const fsp = require('fs').promises;
const FormData = require('form-data');
const EventSource = require('eventsource');
const logger = require('../utils/logger');
const { IS_DEVELOPMENT } = require('../config/env');

async function cleanupFile(filePath) {
  try {
    await fsp.unlink(filePath);
  } catch (error) {
    if (IS_DEVELOPMENT) {
      logger.error('Failed to cleanup file:', filePath, error.message);
    }
  }
}

exports.imageToText = async (req, res, next) => {
  let uploadedFile = null;

  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: 'No image file provided. Please upload an image.'
      });
    }

    uploadedFile = req.file;
    if (IS_DEVELOPMENT) {
      logger.info(`Processing image: ${uploadedFile.originalname}, Size: ${uploadedFile.size} bytes`);
    }

    // --- Send image to Python OCR server (streaming) ---
    const form = new FormData();
    form.append('file', fs.createReadStream(uploadedFile.path));

    const ocrServerUrl = 'http://localhost:1235/imagetotext/stream'; // streaming endpoint

    // Axios doesn't handle SSE natively, so we use EventSource in Node.js
    const es = new EventSource(`${ocrServerUrl}?filename=${encodeURIComponent(uploadedFile.originalname)}`, {
      headers: form.getHeaders(),
    });

    let fullText = '';
    if (IS_DEVELOPMENT) {
      logger.debug('sent to OCR... streaming...');
    }

    es.onmessage = (event) => {
      if (!event.data) return;
      const data = JSON.parse(event.data);
      if (data.text !== undefined) {
        if (IS_DEVELOPMENT) {
          logger.debug(data.text); 
        }
        fullText += data.text + '\n'; 
      }
    };

    es.addEventListener('done', async () => {
      if (IS_DEVELOPMENT) {
        logger.info('OCR success!');
      }

      // Clean up the uploaded file
      await cleanupFile(uploadedFile.path);
      uploadedFile = null;

      // Send final response to the client
      res.json({
        success: true,
        extractedText: fullText.trim(),
        metadata: {
          originalFilename: req.file.originalname,
          fileSize: req.file.size,
          textLength: fullText.trim().length
        }
      });
      es.close();
    });

    es.onerror = async (err) => {
      logger.error('Error streaming from OCR server:', err);
      if (uploadedFile) {
        await cleanupFile(uploadedFile.path);
        uploadedFile = null;
      }
      
      // Only send response if headers haven't been sent
      if (!res.headersSent) {
        res.status(500).json({
          success: false,
          error: 'OCR server streaming failed.',
          details: IS_DEVELOPMENT ? err.message : undefined
        });
      }
      es.close();
    };

  } catch (error) {
    logger.error('Error in /imagetotext:', error);
    if (uploadedFile) {
      await cleanupFile(uploadedFile.path);
    }
    next(error);
  }
};
