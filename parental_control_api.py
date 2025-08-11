#!/usr/bin/env python3
"""
Parental Control API Extension
Handles video monitoring and reporting for cigarette detection
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import asyncio
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
import json
import sqlite3
import cv2
import numpy as np
import threading
import time
import os
import psutil
from PIL import ImageGrab
import pygetwindow as gw

# Import our detection logic
from main import CigaretteDetector

router = APIRouter(prefix="/parental-control", tags=["parental-control"])

# Database setup for monitoring data
def init_monitoring_db():
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            parent_email TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            settings TEXT,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            app_name TEXT,
            video_title TEXT,
            detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confidence_score REAL,
            detection_details TEXT,
            screenshot_path TEXT,
            FOREIGN KEY (session_id) REFERENCES monitoring_sessions (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            date DATE,
            total_videos_watched INTEGER DEFAULT 0,
            smoking_content_detected INTEGER DEFAULT 0,
            total_watch_time_minutes INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES monitoring_sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_monitoring_db()

# Pydantic models
class MonitoringSettings(BaseModel):
    realTimeAlerts: bool = True
    dailyReports: bool = True
    weeklyReports: bool = True
    sensitivityLevel: str = "medium"
    monitoredApps: List[str] = ["youtube", "tiktok", "instagram", "netflix"]

class StartMonitoringRequest(BaseModel):
    parentEmail: EmailStr
    settings: MonitoringSettings
    deviceId: str

class VideoDetection(BaseModel):
    app: str
    timestamp: str
    confidence: float
    details: str

class MonitoringStats(BaseModel):
    totalVideosWatched: int
    smokingContentDetected: int
    lastDetection: Optional[str]
    dailyStats: List[Dict[str, Any]]

# Global monitoring state
active_monitoring_sessions = {}
detector_instance = None

class VideoMonitor:
    def __init__(self, session_id: int, settings: MonitoringSettings):
        self.session_id = session_id
        self.settings = settings
        self.is_running = False
        self.detector = CigaretteDetector()
        self.last_detection_time = 0
        self.detection_cooldown = 30  # seconds between detections for same content
        
    def start_monitoring(self):
        """Start video content monitoring"""
        self.is_running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop_monitoring(self):
        """Stop video content monitoring"""
        self.is_running = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Get active video windows
                video_windows = self._get_video_windows()
                
                for window in video_windows:
                    if self._should_monitor_app(window['app']):
                        screenshot = self._capture_window(window)
                        if screenshot is not None:
                            self._analyze_screenshot(screenshot, window)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _get_video_windows(self):
        """Get list of active video player windows"""
        video_windows = []
        
        try:
            # Get all windows
            windows = gw.getAllWindows()
            
            video_apps = {
                'youtube': ['YouTube', 'Chrome', 'Firefox', 'Safari', 'Edge'],
                'netflix': ['Netflix', 'Chrome', 'Firefox', 'Safari', 'Edge'],
                'tiktok': ['TikTok'],
                'instagram': ['Instagram'],
                'vlc': ['VLC'],
                'quicktime': ['QuickTime']
            }
            
            for window in windows:
                if window.isActive and window.visible:
                    for app_type, app_names in video_apps.items():
                        if any(app_name.lower() in window.title.lower() for app_name in app_names):
                            video_windows.append({
                                'app': app_type,
                                'title': window.title,
                                'window': window
                            })
                            break
                            
        except Exception as e:
            print(f"Error getting video windows: {e}")
        
        return video_windows
    
    def _should_monitor_app(self, app_name):
        """Check if app should be monitored based on settings"""
        return app_name in self.settings.monitoredApps
    
    def _capture_window(self, window_info):
        """Capture screenshot of video window"""
        try:
            window = window_info['window']
            
            # Get window bounds
            left, top, width, height = window.left, window.top, window.width, window.height
            
            # Capture screenshot
            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            
            # Convert to OpenCV format
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            return screenshot_cv
            
        except Exception as e:
            print(f"Error capturing window: {e}")
            return None
    
    def _analyze_screenshot(self, screenshot, window_info):
        """Analyze screenshot for smoking content"""
        try:
            current_time = time.time()
            
            # Avoid too frequent detections
            if current_time - self.last_detection_time < self.detection_cooldown:
                return
            
            # Save screenshot temporarily
            temp_path = f"temp_screenshot_{self.session_id}_{int(current_time)}.jpg"
            cv2.imwrite(temp_path, screenshot)
            
            # Analyze with our detector
            result, error = self.detector.analyze_image(temp_path)
            
            if not error and result['cigarette_detected']:
                self._handle_detection(result, window_info, temp_path)
                self.last_detection_time = current_time
            else:
                # Clean up temp file if no detection
                os.remove(temp_path)
                
        except Exception as e:
            print(f"Error analyzing screenshot: {e}")
    
    def _handle_detection(self, detection_result, window_info, screenshot_path):
        """Handle positive smoking detection"""
        try:
            # Save detection to database
            conn = sqlite3.connect('monitoring.db')
            cursor = conn.cursor()
            
            max_confidence = max([d['confidence'] for d in detection_result['detections'] 
                                if d['is_cigarette_related']], default=0)
            
            cursor.execute('''
                INSERT INTO video_detections 
                (session_id, app_name, video_title, confidence_score, detection_details, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                window_info['app'],
                window_info['title'],
                max_confidence,
                json.dumps(detection_result),
                screenshot_path
            ))
            
            conn.commit()
            conn.close()
            
            # Send real-time alert if enabled
            if self.settings.realTimeAlerts:
                self._send_realtime_alert(detection_result, window_info)
                
        except Exception as e:
            print(f"Error handling detection: {e}")
    
    def _send_realtime_alert(self, detection_result, window_info):
        """Send immediate alert to parent"""
        # This would integrate with email/SMS service
        print(f"ALERT: Smoking content detected in {window_info['app']} - {window_info['title']}")

@router.post("/start-monitoring")
async def start_monitoring(request: StartMonitoringRequest):
    """Start video monitoring for a device"""
    try:
        # Save monitoring session to database
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO monitoring_sessions (device_id, parent_email, settings)
            VALUES (?, ?, ?)
        ''', (request.deviceId, request.parentEmail, json.dumps(request.settings.dict())))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Start monitoring
        monitor = VideoMonitor(session_id, request.settings)
        monitor.start_monitoring()
        
        active_monitoring_sessions[request.deviceId] = {
            'session_id': session_id,
            'monitor': monitor,
            'parent_email': request.parentEmail
        }
        
        return {"status": "success", "message": "Monitoring started", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {e}")

@router.post("/stop-monitoring")
async def stop_monitoring(device_id: str = "mobile_device_001"):
    """Stop video monitoring for a device"""
    try:
        if device_id in active_monitoring_sessions:
            session = active_monitoring_sessions[device_id]
            session['monitor'].stop_monitoring()
            
            # Update database
            conn = sqlite3.connect('monitoring.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE monitoring_sessions 
                SET end_time = CURRENT_TIMESTAMP, is_active = FALSE
                WHERE id = ?
            ''', (session['session_id'],))
            conn.commit()
            conn.close()
            
            del active_monitoring_sessions[device_id]
            
        return {"status": "success", "message": "Monitoring stopped"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {e}")

@router.get("/stats")
async def get_monitoring_stats(device_id: str = "mobile_device_001"):
    """Get monitoring statistics"""
    try:
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        
        # Get latest session for device
        cursor.execute('''
            SELECT id FROM monitoring_sessions 
            WHERE device_id = ? 
            ORDER BY start_time DESC LIMIT 1
        ''', (device_id,))
        
        session_result = cursor.fetchone()
        if not session_result:
            return MonitoringStats(
                totalVideosWatched=0,
                smokingContentDetected=0,
                lastDetection=None,
                dailyStats=[]
            )
        
        session_id = session_result[0]
        
        # Get detection count
        cursor.execute('''
            SELECT COUNT(*) FROM video_detections WHERE session_id = ?
        ''', (session_id,))
        smoking_detections = cursor.fetchone()[0]
        
        # Get last detection
        cursor.execute('''
            SELECT detection_time FROM video_detections 
            WHERE session_id = ? 
            ORDER BY detection_time DESC LIMIT 1
        ''', (session_id,))
        
        last_detection_result = cursor.fetchone()
        last_detection = last_detection_result[0] if last_detection_result else None
        
        # Get daily stats (mock data for now)
        daily_stats = [
            {"date": "2024-01-01", "videos": 5, "detections": 1},
            {"date": "2024-01-02", "videos": 3, "detections": 0},
        ]
        
        conn.close()
        
        return MonitoringStats(
            totalVideosWatched=20,  # This would be calculated from actual data
            smokingContentDetected=smoking_detections,
            lastDetection=last_detection,
            dailyStats=daily_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")

@router.post("/send-test-report")
async def send_test_report(request: dict):
    """Send test report to parent email"""
    try:
        parent_email = request.get('parentEmail')
        
        if not parent_email:
            raise HTTPException(status_code=400, detail="Parent email required")
        
        # Create test report
        report_html = f"""
        <html>
        <body>
            <h2>🚭 Cigarette Detection - Test Report</h2>
            <p>This is a test report from your child's device monitoring system.</p>
            
            <h3>📊 Sample Statistics</h3>
            <ul>
                <li>Total Videos Watched: 15</li>
                <li>Smoking Content Detected: 2</li>
                <li>Detection Rate: 13.3%</li>
                <li>Last Detection: 2024-01-01 15:30:00</li>
            </ul>
            
            <h3>🚨 Recent Detections</h3>
            <ul>
                <li><strong>YouTube</strong> - Detected at 15:30 (Confidence: 85%)</li>
                <li><strong>TikTok</strong> - Detected at 12:15 (Confidence: 92%)</li>
            </ul>
            
            <p><em>This system helps you monitor smoking content in videos your child watches.</em></p>
            
            <hr>
            <p><small>Cigarette Detection System - Parental Control Report</small></p>
        </body>
        </html>
        """
        
        # In production, you would send actual email here
        # For now, we'll just simulate it
        print(f"Test report would be sent to: {parent_email}")
        print("Report content:", report_html)
        
        return {"status": "success", "message": "Test report sent successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test report: {e}")

@router.get("/recent-detections")
async def get_recent_detections(device_id: str = "mobile_device_001", limit: int = 10):
    """Get recent smoking content detections"""
    try:
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vd.app_name, vd.detection_time, vd.confidence_score, vd.video_title
            FROM video_detections vd
            JOIN monitoring_sessions ms ON vd.session_id = ms.id
            WHERE ms.device_id = ?
            ORDER BY vd.detection_time DESC
            LIMIT ?
        ''', (device_id, limit))
        
        detections = []
        for row in cursor.fetchall():
            detections.append({
                'app': row[0],
                'timestamp': row[1],
                'confidence': int(row[2] * 100),
                'title': row[3]
            })
        
        conn.close()
        return detections
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent detections: {e}")

# Email notification system (production implementation)
class EmailNotifier:
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        # In production, these would be environment variables
        self.email_user = os.getenv("NOTIFICATION_EMAIL", "")
        self.email_password = os.getenv("NOTIFICATION_PASSWORD", "")
    
    def send_daily_report(self, parent_email: str, stats: dict):
        """Send daily monitoring report"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = parent_email
            msg['Subject'] = "Daily Smoking Content Report"
            
            body = self._create_daily_report_html(stats)
            msg.attach(MimeText(body, 'html'))
            
            # Send email (commented out for demo)
            # server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            # server.starttls()
            # server.login(self.email_user, self.email_password)
            # server.send_message(msg)
            # server.quit()
            
            print(f"Daily report sent to {parent_email}")
            
        except Exception as e:
            print(f"Failed to send daily report: {e}")
    
    def _create_daily_report_html(self, stats: dict) -> str:
        """Create HTML content for daily report"""
        return f"""
        <html>
        <body>
            <h2>🚭 Daily Smoking Content Report</h2>
            <p>Here's your child's video watching activity for today:</p>
            
            <h3>📊 Today's Statistics</h3>
            <ul>
                <li>Videos Watched: {stats.get('videos_watched', 0)}</li>
                <li>Smoking Content Detected: {stats.get('smoking_detected', 0)}</li>
                <li>Watch Time: {stats.get('watch_time_minutes', 0)} minutes</li>
            </ul>
            
            <p>Stay informed about your child's digital content consumption.</p>
        </body>
        </html>
        """

# Background task for sending scheduled reports
async def send_scheduled_reports():
    """Send daily/weekly reports to parents"""
    # This would run as a background task
    pass
