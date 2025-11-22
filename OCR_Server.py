from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, StreamingResponse
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import io
import uvicorn
import json

app = FastAPI()

# Default OCR for English
ocr_en = PaddleOCR(use_textline_orientation=True, lang='en')

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

@app.post("/imagetotext")
async def imagetotext(file: UploadFile, lang: str = Form(None)):
    """
    Return JSON response with extracted text
    'lang' can be provided; defaults to English if not sent.
    """
    try:
        # Read image
        image_bytes = await file.read()
        img = np.array(Image.open(io.BytesIO(image_bytes)))

        # Choose OCR instance
        if lang is None or lang.lower() == 'en':
            ocr = ocr_en
        else:
            ocr = PaddleOCR(use_textline_orientation=True, lang=lang)

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
        image_bytes = await file.read()
        img = np.array(Image.open(io.BytesIO(image_bytes)))

        # Choose OCR instance
        if lang is None or lang.lower() == 'en':
            ocr = ocr_en
        else:
            ocr = PaddleOCR(use_textline_orientation=True, lang=lang)

        results = ocr.predict(img)
        lines = results[0]['rec_texts'] if results else []

        def event_generator():
            for line in lines:
                yield f"data: {json.dumps({'text': line})}\n\n"
            # Signal end
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        def error_gen():
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1235)
    print("Server is now running!")
