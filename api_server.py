#!/usr/bin/env python3
"""
FastAPI Backend Server for Cigarette Detection System
Includes image detection, parental control, and app protection features
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
import os
import shutil
from datetime import datetime
import sqlite3
import threading
import time

# Import our detection logic
from main import SmokingVapingDetector

# Import self-monitoring API
from parental_control_api import router as self_monitoring_router

# Import app protection system
from app_protection import AppProtectionSystem
from alerts import alert_manager, set_event_loop

# FastAPI app initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register event loop for cross-thread WebSocket broadcasts
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.get_running_loop()
    set_event_loop(loop)
    yield

app = FastAPI(
    title="Vaping and Smoking Detection System",
    description="AI-powered detection of smoking in images and videos, including vaping devices and cigarettes.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include self-monitoring router
app.include_router(self_monitoring_router)

# WebSocket endpoint for real-time alerts
@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await alert_manager.connect(websocket)
    try:
        print("[WS] client connected")
        while True:
            # Keep the connection alive; we don't expect client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_manager.disconnect(websocket)
        print("[WS] client disconnected")

# Simple test endpoint to verify alerts pipeline end-to-end
@app.post("/alerts/test")
async def send_test_alert(kind: str = "smoking", confidence: float = 0.87):
    """Broadcast a test detection alert to all connected WebSocket clients.
    Call with: curl -X POST "http://localhost:8000/alerts/test?kind=vaping&confidence=0.92"
    """
    message = {
        "type": "detection",
        "label": "Vaping and Smoking Detection",
        "detection_type": kind,
        "max_confidence": float(confidence),
        "timestamp": time.time(),
        "screenshot_path": None,
    }
    await alert_manager.broadcast(message)
    return {"status": "ok", "message": message}

# Serve static files and web frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("web_frontend.html")

@app.get("/simple")
async def serve_simple_frontend():
    return FileResponse("simple_frontend.html")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("manifest.json")

# Global instances
detector = SmokingVapingDetector()
protection_system = AppProtectionSystem()

# Job management
jobs_db = "jobs.db"
active_jobs = {}

# Pydantic models
class DetectionResult(BaseModel):
    filename: str
    cigarette_detected: bool
    max_confidence: float
    detections: List[Dict[str, Any]]

class BatchJobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[Dict[str, int]] = None
    error: Optional[str] = None

class BatchJobResults(BaseModel):
    job_id: str
    results: List[DetectionResult]
    summary: Dict[str, Any]

# Database initialization
def init_jobs_db():
    """Initialize jobs database"""
    conn = sqlite3.connect(jobs_db)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_images INTEGER,
            processed_images INTEGER DEFAULT 0,
            error_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            filename TEXT,
            cigarette_detected BOOLEAN,
            max_confidence REAL,
            detection_details TEXT,
            FOREIGN KEY (job_id) REFERENCES batch_jobs (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_jobs_db()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Single image detection
@app.post("/detect/single")
async def detect_single_image(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.5)
):
    """Analyze a single image for cigarette detection"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save uploaded file temporarily
        temp_filename = f"temp_{uuid.uuid4().hex}_{file.filename}"
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Analyze image
        result, error = detector.analyze_image(temp_filename, confidence_threshold)
        
        # Clean up temp file
        os.remove(temp_filename)
        
        if error:
            raise HTTPException(status_code=500, detail=f"Detection error: {error}")
        
        return {
            "success": True,
            "filename": file.filename,
            "cigarette_detected": result.get("cigarette_detected", False),  # Backward compatibility
            "smoking_detected": result.get("smoking_detected", False),
            "vaping_detected": result.get("vaping_detected", False),
            "any_detected": result.get("any_detected", False),
            "detection_types": result.get("detection_types", []),
            "confidence": result.get("max_confidence", 0.0),
            "total_detections": result.get("total_detections", 0),
            "analysis_time": result.get("analysis_time", 0.0),
            "detections": result.get("detections", []),
            "message": f"Analysis complete. Found: {', '.join(result.get('detection_types', ['none']))}"
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

# Batch image detection
@app.post("/detect/batch")
async def detect_batch_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    confidence_threshold: float = Form(0.5)
):
    """Analyze multiple images for cigarette detection"""
    try:
        if len(files) > 50:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum 50 files allowed per batch")
        
        # Create job
        job_id = str(uuid.uuid4())
        
        # Save job to database
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO batch_jobs (id, status, total_images)
            VALUES (?, ?, ?)
        ''', (job_id, "processing", len(files)))
        conn.commit()
        conn.close()
        
        # Save files temporarily
        temp_files = []
        for file in files:
            if not file.content_type.startswith('image/'):
                continue
            
            temp_filename = f"temp_{job_id}_{file.filename}"
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append((temp_filename, file.filename))
        
        # Start background processing
        background_tasks.add_task(
            process_batch_job, 
            job_id, 
            temp_files, 
            confidence_threshold
        )
        
        return {"job_id": job_id, "status": "processing", "total_images": len(temp_files)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Apple Photos detection
@app.post("/detect/apple-photos")
async def detect_apple_photos(
    background_tasks: BackgroundTasks,
    confidence_threshold: float = Form(0.5),
    limit: int = Form(100)
):
    """Analyze Apple Photos library for cigarette detection"""
    try:
        job_id = str(uuid.uuid4())
        
        # Start background processing
        background_tasks.add_task(
            process_apple_photos_job,
            job_id,
            confidence_threshold,
            limit
        )
        
        return {"job_id": job_id, "status": "processing", "message": "Apple Photos analysis started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Job status endpoint
@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get status of a batch job"""
    try:
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, total_images, processed_images, error_message
            FROM batch_jobs WHERE id = ?
        ''', (job_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        status, total, processed, error = result
        
        response = {
            "job_id": job_id,
            "status": status,
            "progress": {
                "total": total or 0,
                "processed": processed or 0
            }
        }
        
        if error:
            response["error"] = error
            
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Job results endpoint
@app.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Get results of a completed batch job"""
    try:
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        
        # Check job status
        cursor.execute('SELECT status FROM batch_jobs WHERE id = ?', (job_id,))
        job_result = cursor.fetchone()
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_result[0] != "completed":
            raise HTTPException(status_code=400, detail="Job not completed yet")
        
        # Get results
        cursor.execute('''
            SELECT filename, cigarette_detected, max_confidence, detection_details
            FROM job_results WHERE job_id = ?
        ''', (job_id,))
        
        results = []
        total_detected = 0
        
        for row in cursor.fetchall():
            filename, detected, confidence, details = row
            
            if detected:
                total_detected += 1
            
            results.append({
                "filename": filename,
                "cigarette_detected": bool(detected),
                "max_confidence": confidence,
                "detections": json.loads(details) if details else []
            })
        
        conn.close()
        
        return {
            "job_id": job_id,
            "results": results,
            "summary": {
                "total_images": len(results),
                "images_with_cigarettes": total_detected,
                "detection_rate": (total_detected / len(results) * 100) if results else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# App Protection endpoints
@app.post("/protection/enable")
async def enable_app_protection(request: dict):
    """Enable app protection for a device"""
    try:
        device_id = request.get('deviceId', 'unknown_device')
        parent_email = request.get('parentEmail')
        
        if not parent_email:
            raise HTTPException(status_code=400, detail="Parent email required")
        
        # Register and start protection
        success = protection_system.register_installation(device_id, parent_email)
        
        if success:
            protection_system.start_protection(device_id)
            return {"status": "success", "message": "App protection enabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to enable protection")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Protection error: {e}")

@app.post("/protection/disable")
async def disable_app_protection():
    """Disable app protection"""
    try:
        protection_system.stop_protection()
        return {"status": "success", "message": "App protection disabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable protection: {e}")

@app.get("/protection/status")
async def get_protection_status(device_id: str = "unknown_device"):
    """Get app protection status"""
    try:
        status = protection_system.get_protection_status(device_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get protection status: {e}")

# Background task functions
async def process_batch_job(job_id: str, temp_files: List[tuple], confidence_threshold: float):
    """Process batch job in background"""
    try:
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        
        processed = 0
        
        for temp_filename, original_filename in temp_files:
            try:
                # Analyze image
                result, error = detector.analyze_image(temp_filename, confidence_threshold)
                
                if not error:
                    # Save result to database
                    cursor.execute('''
                        INSERT INTO job_results 
                        (job_id, filename, cigarette_detected, max_confidence, detection_details)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        job_id,
                        original_filename,
                        result["cigarette_detected"],
                        result["max_confidence"],
                        json.dumps(result["detections"])
                    ))
                
                processed += 1
                
                # Update progress
                cursor.execute('''
                    UPDATE batch_jobs 
                    SET processed_images = ? 
                    WHERE id = ?
                ''', (processed, job_id))
                
                conn.commit()
                
                # Clean up temp file
                os.remove(temp_filename)
                
            except Exception as e:
                print(f"Error processing {original_filename}: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
        
        # Mark job as completed
        cursor.execute('''
            UPDATE batch_jobs 
            SET status = ?, completed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', ("completed", job_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        # Mark job as failed
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE batch_jobs 
            SET status = ?, error_message = ? 
            WHERE id = ?
        ''', ("failed", str(e), job_id))
        conn.commit()
        conn.close()

async def process_apple_photos_job(job_id: str, confidence_threshold: float, limit: int):
    """Process Apple Photos in background"""
    try:
        # Get Apple Photos
        photos = detector.get_apple_photos(limit)
        
        if not photos:
            raise Exception("No photos found or unable to access Apple Photos")
        
        # Save job to database
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO batch_jobs (id, status, total_images)
            VALUES (?, ?, ?)
        ''', (job_id, "processing", len(photos)))
        conn.commit()
        
        processed = 0
        
        for photo_path in photos:
            try:
                result, error = detector.analyze_image(photo_path, confidence_threshold)
                
                if not error:
                    cursor.execute('''
                        INSERT INTO job_results 
                        (job_id, filename, cigarette_detected, max_confidence, detection_details)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        job_id,
                        os.path.basename(photo_path),
                        result["cigarette_detected"],
                        result["max_confidence"],
                        json.dumps(result["detections"])
                    ))
                
                processed += 1
                cursor.execute('''
                    UPDATE batch_jobs 
                    SET processed_images = ? 
                    WHERE id = ?
                ''', (processed, job_id))
                conn.commit()
                
            except Exception as e:
                print(f"Error processing {photo_path}: {e}")
        
        # Mark as completed
        cursor.execute('''
            UPDATE batch_jobs 
            SET status = ?, completed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', ("completed", job_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        conn = sqlite3.connect(jobs_db)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE batch_jobs 
            SET status = ?, error_message = ? 
            WHERE id = ?
        ''', ("failed", str(e), job_id))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
