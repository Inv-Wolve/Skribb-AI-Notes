from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import io
import uvicorn
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Skribb AI OCR Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR engines (lazy loading could be better, but keeping it simple for now)
try:
    logger.info("Initializing English OCR engine...")
    ocr_en = PaddleOCR(use_textline_orientation=True, lang='en', show_log=False)
    logger.info("English OCR engine initialized.")
except Exception as e:
    logger.error(f"Failed to initialize OCR engine: {e}")
    ocr_en = None

def sanitize_for_json(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "ocr_engine": "ready" if ocr_en else "failed"}

@app.post("/imagetotext")
async def imagetotext(file: UploadFile, lang: str = Form(None)):
    """
    Return JSON response with extracted text
    """
    try:
        if not ocr_en:
             return JSONResponse({"success": False, "error": "OCR engine not initialized"}, status_code=500)

        # Read image
        image_bytes = await file.read()
        img = np.array(Image.open(io.BytesIO(image_bytes)))

        # Choose OCR instance (currently only EN supported efficiently)
        ocr = ocr_en
        if lang and lang.lower() != 'en':
             # Dynamic loading for other languages (might be slow)
             logger.info(f"Loading OCR for language: {lang}")
             ocr = PaddleOCR(use_textline_orientation=True, lang=lang, show_log=False)

        # Run OCR
        results = ocr.predict(img)
        text_lines = results[0]['rec_texts'] if results else []

        serializable_results = sanitize_for_json(results)
        extracted_text = " ".join(text_lines)

        return JSONResponse({
            "success": True,
            "text": extracted_text,
            "raw_result": serializable_results,
            "lang_used": lang if lang else "en"
        })

    except Exception as e:
        logger.error(f"Error in imagetotext: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/imagetotext/stream")
async def imagetotext_stream(file: UploadFile, lang: str = Form(None)):
    """
    Streaming endpoint for Server-Sent Events (SSE)
    """
    try:
        if not ocr_en:
             raise Exception("OCR engine not initialized")

        image_bytes = await file.read()
        img = np.array(Image.open(io.BytesIO(image_bytes)))

        ocr = ocr_en
        if lang and lang.lower() != 'en':
             ocr = PaddleOCR(use_textline_orientation=True, lang=lang, show_log=False)

        results = ocr.predict(img)
        lines = results[0]['rec_texts'] if results else []

        def event_generator():
            for line in lines:
                yield f"data: {json.dumps({'text': line})}\n\n"
            # Signal end
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in imagetotext_stream: {e}")
        def error_gen():
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1235)