#!/usr/bin/env python3
"""
Handwriting OCR Upload Service

A FastAPI-based service for collecting handwriting samples, performing OCR,
and managing training data for custom handwriting recognition models.
"""

import os
import uuid
import json
import io
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import hashlib
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, Form, HTTPException, Header, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uploads.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration."""
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "changeme")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    USE_OCR: bool = os.getenv("USE_OCR", "true").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "1234"))
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")

config = Config()

# OCR Setup
ocr_engine = None
if config.USE_OCR:
    try:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
        logger.info("PaddleOCR initialized successfully")
    except ImportError:
        logger.warning("PaddleOCR not available. Install with: pip install paddleocr")
        config.USE_OCR = False
    except Exception as e:
        logger.error(f"Failed to initialize PaddleOCR: {e}")
        config.USE_OCR = False

# Directory setup
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
APPROVED_DIR = DATA_DIR / "approved"
LABELS_FILE = DATA_DIR / "labels.json"

# Pydantic models
class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    success: bool
    upload_id: str
    predicted: Optional[str] = None
    message: str = "Upload successful"

class UploadMetadata(BaseModel):
    """Model for upload metadata."""
    id: str
    file: str
    orig_name: str
    provided_text: str = ""
    predicted_text: str = ""
    corrected_text: str = ""
    status: str = "pending"
    notes: str = ""
    upload_time: str
    file_size: int
    file_hash: str

class AdminResponse(BaseModel):
    """Response model for admin operations."""
    success: bool
    message: str = ""

# Data management
class DataManager:
    """Handles data persistence and management."""
    
    def __init__(self):
        self._setup_directories()
        self.labels = self._load_labels()
    
    def _setup_directories(self) -> None:
        """Create necessary directories."""
        directories = [DATA_DIR, IMAGES_DIR, APPROVED_DIR]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def _load_labels(self) -> Dict[str, Dict]:
        """Load labels from JSON file."""
        if not LABELS_FILE.exists():
            logger.info("Labels file doesn't exist, starting with empty dataset")
            return {}
        
        try:
            with open(LABELS_FILE, "r", encoding="utf-8") as f:
                labels = json.load(f)
            logger.info(f"Loaded {len(labels)} existing labels")
            return labels
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted labels file: {e}")
            # Backup corrupted file
            backup_file = LABELS_FILE.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            LABELS_FILE.rename(backup_file)
            logger.info(f"Corrupted file backed up to: {backup_file}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")
            return {}
    
    def save_labels(self) -> None:
        """Save labels to JSON file with atomic write."""
        temp_file = LABELS_FILE.with_suffix('.tmp')
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.labels, f, ensure_ascii=False, indent=2)
            temp_file.replace(LABELS_FILE)
            logger.debug("Labels saved successfully")
        except Exception as e:
            logger.error(f"Failed to save labels: {e}")
            temp_file.unlink(missing_ok=True)
            raise
    
    def add_upload(self, upload_id: str, metadata: Dict) -> None:
        """Add new upload metadata."""
        self.labels[upload_id] = metadata
        self.save_labels()
    
    def update_upload(self, upload_id: str, updates: Dict) -> bool:
        """Update existing upload metadata."""
        if upload_id not in self.labels:
            return False
        self.labels[upload_id].update(updates)
        self.save_labels()
        return True
    
    def delete_upload(self, upload_id: str) -> bool:
        """Delete upload metadata."""
        if upload_id not in self.labels:
            return False
        del self.labels[upload_id]
        self.save_labels()
        return True
    
    def get_upload(self, upload_id: str) -> Optional[Dict]:
        """Get upload metadata by ID."""
        return self.labels.get(upload_id)
    
    def get_all_uploads(self) -> List[Dict]:
        """Get all upload metadata."""
        return list(self.labels.values())

# Utility functions
def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (this is approximate, actual size checked after reading)
    if hasattr(file, 'size') and file.size and file.size > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
        )

def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()

async def run_ocr(image_bytes: bytes) -> Optional[str]:
    """Run OCR on image bytes."""
    if not config.USE_OCR or not ocr_engine:
        return None
    
    try:
        from PIL import Image
        import numpy as np
        
        # Convert bytes to numpy array
        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        
        # Run OCR
        results = ocr_engine.ocr(img)
        
        if not results or not results[0]:
            return None
        
        # Extract text from results
        lines = []
        for line in results[0]:
            if line and len(line) >= 2 and line[1]:
                text, confidence = line[1]
                if confidence > 0.5:  # Only include high-confidence results
                    lines.append(text)
        
        return " ".join(lines) if lines else None
        
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return None

def verify_admin_token(admin_token: Optional[str] = Header(None, alias="x-admin-token")) -> str:
    """Verify admin token."""
    if not admin_token or admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return admin_token

# Initialize data manager
data_manager = DataManager()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Handwriting OCR Upload Service")
    logger.info(f"OCR enabled: {config.USE_OCR}")
    logger.info(f"Data directory: {DATA_DIR}")
    yield
    logger.info("Shutting down Handwriting OCR Upload Service")

# FastAPI app
app = FastAPI(
    title="Handwriting OCR Upload Service",
    description="A service for collecting and managing handwriting samples for OCR training",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Static file serving
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/approved", StaticFiles(directory=APPROVED_DIR), name="approved")

# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_upload_page():
    """Serve the main upload page."""
    upload_file = BASE_DIR / "upload.html"
    if not upload_file.exists():
        raise HTTPException(status_code=404, detail="Upload page not found")
    return FileResponse(upload_file)

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_page():
    """Serve the admin page."""
    admin_file = BASE_DIR / "admin.html"
    if not admin_file.exists():
        raise HTTPException(status_code=404, detail="Admin page not found")
    return FileResponse(admin_file)

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile,
    text: Optional[str] = Form(None)
):
    """Upload handwriting sample with optional transcription."""
    # Validate file
    validate_file(file)
    
    # Read file content
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file")
    
    # Check file size
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(contents) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
        )
    
    # Generate unique ID and file hash
    upload_id = str(uuid.uuid4())
    file_hash = calculate_file_hash(contents)
    
    # Check for duplicate files
    for existing_id, existing_data in data_manager.labels.items():
        if existing_data.get("file_hash") == file_hash:
            logger.warning(f"Duplicate file detected: {file.filename} (hash: {file_hash[:8]}...)")
            return UploadResponse(
                success=True,
                upload_id=existing_id,
                predicted=existing_data.get("predicted_text"),
                message="File already exists in system"
            )
    
    # Save file with unique name (ignore original filename)
    # Detect file type from content or use original extension as fallback
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        # Map MIME types to extensions
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg", 
            "image/png": ".png",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/webp": ".webp"
        }
        ext = mime_to_ext.get(content_type, ".jpg")
    else:
        # Fallback to original extension or default
        ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        if ext not in config.ALLOWED_EXTENSIONS:
            ext = ".jpg"
    
    # Always use unique ID as filename
    save_name = f"{upload_id}{ext}"
    save_path = IMAGES_DIR / save_name
    
    try:
        with open(save_path, "wb") as f:
            f.write(contents)
        logger.info(f"Saved file: {save_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    # Run OCR
    prediction = await run_ocr(contents) if config.USE_OCR else None
    
    # Create metadata
    metadata = {
        "id": upload_id,
        "file": save_name,
        "orig_name": file.filename,
        "provided_text": text or "",
        "predicted_text": prediction or "",
        "corrected_text": "",
        "status": "pending",
        "notes": "",
        "upload_time": datetime.now().isoformat(),
        "file_size": len(contents),
        "file_hash": file_hash,
    }
    
    # Save metadata
    try:
        data_manager.add_upload(upload_id, metadata)
        logger.info(f"Created upload record: {upload_id}")
    except Exception as e:
        # Clean up file if metadata save fails
        save_path.unlink(missing_ok=True)
        logger.error(f"Failed to save metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to save upload metadata")
    
    return UploadResponse(
        success=True,
        upload_id=upload_id,
        predicted=prediction,
        message="Upload successful"
    )

@app.get("/admin/uploads")
async def admin_list_uploads(admin_token: str = Depends(verify_admin_token)) -> List[Dict]:
    """List all uploads (admin only)."""
    try:
        uploads = data_manager.get_all_uploads()
        logger.info(f"Admin retrieved {len(uploads)} uploads")
        return uploads
    except Exception as e:
        logger.error(f"Failed to retrieve uploads: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve uploads")

@app.post("/admin/approve", response_model=AdminResponse)
async def admin_approve_upload(
    upload_id: str = Form(...),
    corrected_text: str = Form(...),
    admin_token: str = Depends(verify_admin_token)
):
    """Approve upload and move to training data."""
    # Validate inputs
    if not upload_id or not upload_id.strip():
        raise HTTPException(status_code=400, detail="Upload ID is required")
    
    if not corrected_text or not corrected_text.strip():
        raise HTTPException(status_code=400, detail="Corrected text is required")
    
    upload_id = upload_id.strip()
    corrected_text = corrected_text.strip()
    
    entry = data_manager.get_upload(upload_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Move file to approved directory
    src_path = IMAGES_DIR / entry["file"]
    dst_path = APPROVED_DIR / entry["file"]
    
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found")
    
    try:
        src_path.rename(dst_path)
        logger.info(f"Moved file to approved: {src_path} -> {dst_path}")
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        raise HTTPException(status_code=500, detail="Failed to move file")
    
    # Update metadata
    updates = {
        "status": "approved",
        "corrected_text": corrected_text,
        "notes": "approved by admin",
        "approval_time": datetime.now().isoformat()
    }
    
    try:
        data_manager.update_upload(upload_id, updates)
        logger.info(f"Approved upload: {upload_id}")
    except Exception as e:
        # Try to move file back
        try:
            dst_path.rename(src_path)
        except:
            pass
        logger.error(f"Failed to update metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to update upload")
    
    return AdminResponse(success=True, message="Upload approved successfully")

@app.post("/admin/reject", response_model=AdminResponse)
async def admin_reject_upload(
    upload_id: str = Form(...),
    reason: Optional[str] = Form(None),
    admin_token: str = Depends(verify_admin_token)
):
    """Reject upload."""
    entry = data_manager.get_upload(upload_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    updates = {
        "status": "rejected",
        "notes": reason or "rejected by admin",
        "rejection_time": datetime.now().isoformat()
    }
    
    try:
        data_manager.update_upload(upload_id, updates)
        logger.info(f"Rejected upload: {upload_id}")
    except Exception as e:
        logger.error(f"Failed to update metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to update upload")
    
    return AdminResponse(success=True, message="Upload rejected successfully")

@app.delete("/admin/delete/{upload_id}", response_model=AdminResponse)
async def admin_delete_upload(
    upload_id: str,
    admin_token: str = Depends(verify_admin_token)
):
    """Delete upload permanently."""
    entry = data_manager.get_upload(upload_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Delete file from both possible locations
    file_paths = [
        IMAGES_DIR / entry["file"],
        APPROVED_DIR / entry["file"]
    ]
    
    deleted_files = []
    for file_path in file_paths:
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_files.append(str(file_path))
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
    
    # Delete metadata
    try:
        data_manager.delete_upload(upload_id)
        logger.info(f"Deleted upload metadata: {upload_id}")
    except Exception as e:
        logger.error(f"Failed to delete metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete upload metadata")
    
    return AdminResponse(
        success=True, 
        message=f"Upload deleted successfully. Files removed: {len(deleted_files)}"
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ocr_enabled": config.USE_OCR,
        "total_uploads": len(data_manager.labels),
        "approved_uploads": len([u for u in data_manager.labels.values() if u.get("status") == "approved"]),
        "pending_uploads": len([u for u in data_manager.labels.values() if u.get("status") == "pending"])
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    uploads = data_manager.get_all_uploads()
    
    stats = {
        "total_uploads": len(uploads),
        "status_breakdown": {},
        "total_file_size": 0,
        "average_file_size": 0,
        "ocr_enabled": config.USE_OCR
    }
    
    # Calculate statistics
    for upload in uploads:
        status = upload.get("status", "unknown")
        stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
        stats["total_file_size"] += upload.get("file_size", 0)
    
    if len(uploads) > 0:
        stats["average_file_size"] = stats["total_file_size"] / len(uploads)
    
    return stats

# Error handlers
@app.exception_handler(413)
async def file_too_large_handler(request: Request, exc: HTTPException):
    """Handle file too large errors."""
    return JSONResponse(
        status_code=413,
        content={"detail": f"File too large. Maximum size: {config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"}
    )

def main():
    """Main function to run the server."""
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(
        "uploads:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()