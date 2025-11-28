const express = require('express');
const multer = require('multer');
const aiController = require('../controllers/aiController');
const ocrController = require('../controllers/ocrController');

const router = express.Router();

// Multer configuration for file uploads
const upload = multer({
  dest: 'uploads/',
  limits: {
    fileSize: 15 * 1024 * 1024, // 15MB limit
  },
  fileFilter: (req, file, cb) => {
    // Accept only image files
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only image files are allowed'), false);
    }
  }
});

// AI Routes
router.post('/txt-enhance', aiController.enhanceText);
router.post('/txt-fix', aiController.fixText);
router.post('/code-enhance', aiController.enhanceCode);

// OCR Routes
router.post('/imagetotext', upload.single('image'), ocrController.imageToText);

module.exports = router;
