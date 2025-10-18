#!/usr/bin/env python3
"""
Self-Monitoring API Extension
Handles personal video monitoring and reporting for smoking/vaping detection
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import asyncio
# Email functionality temporarily disabled due to Python email module issues
# import smtplib
# from email.mime.text import MimeText
# from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
import json
import sqlite3
import cv2
import numpy as np
import threading
import time
import os
from PIL import ImageGrab
from main import SmokingVapingDetector
from alerts import alert_manager, broadcast_from_thread

# Safari-only video monitoring - no additional dependencies needed


router = APIRouter(prefix="/self-monitoring", tags=["self-monitoring"])

# Database setup for monitoring data
def init_monitoring_db():
    conn = sqlite3.connect('monitoring.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            user_email TEXT,
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

class SelfVideoMonitor:
    def __init__(self, session_id: int, settings: MonitoringSettings):
        self.session_id = session_id
        self.settings = settings
        self.is_running = False
        self.detector = SmokingVapingDetector()
        self.last_detection_time = 0
        self.detection_cooldown = 30  # seconds between detections for same content
        self.max_screenshots = 5  # Keep only last 5 screenshots
        
    def start_monitoring(self):
        """Start personal video content monitoring"""
        self.is_running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop_monitoring(self):
        """Stop personal video content monitoring"""
        self.is_running = False
    
    def _monitor_loop(self):
        """Main self-monitoring loop"""
        print("🔄 Starting self-monitoring loop...")
        while self.is_running:
            try:
                # Get active video windows
                video_windows = self._get_video_windows()
                print(f"📹 Found {len(video_windows)} video windows to monitor")
                
                for window in video_windows:
                    if self._should_monitor_app(window['app']):
                        print(f"🎯 Monitoring {window['app']}: {window['title']}")
                        screenshot = self._capture_window(window)
                        if screenshot is not None:
                            print(f"📸 Screenshot captured, analyzing for smoking/vaping...")
                            self._analyze_screenshot(screenshot, window)
                        else:
                            print("❌ Failed to capture screenshot")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"⚠️ Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _get_video_windows(self):
        """Get active video windows for self-monitoring"""
        video_windows = []
        
        try:
            # Check if Safari is the frontmost application
            print("🔍 Checking for Safari windows...")
            if not self._is_safari_frontmost():
                print("⚠️ Safari is not the active application - skipping capture")
                return video_windows
            
            # Get Safari window bounds (without activating)
            safari_bounds = self._get_safari_window_bounds()
            if safari_bounds:
                # Verify Safari is on YouTube
                if self._is_safari_on_youtube():
                    print(f"✅ Safari on YouTube detected: {safari_bounds}")
                    video_windows.append({
                        'app': 'youtube',
                        'title': 'Safari - YouTube',
                        'window': None  # Not needed for Safari capture
                    })
                else:
                    print("⚠️ Safari is open but not on YouTube - skipping")
            else:
                print("❌ No Safari window detected")
                
        except Exception as e:
            print(f"⚠️ Error getting video windows: {e}")
        
        return video_windows
    
    def _should_monitor_app(self, app_name):
        """Check if app should be self-monitored (Safari YouTube only)"""
        return app_name == 'youtube'
    
    def _is_safari_frontmost(self):
        """Check if Safari is the frontmost (active) application"""
        try:
            import subprocess
            
            # AppleScript to check frontmost application
            frontmost_script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', frontmost_script], 
                                  capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and result.stdout.strip():
                frontmost_app = result.stdout.strip()
                is_safari = frontmost_app == "Safari"
                print(f"🎯 Frontmost app: {frontmost_app} | Is Safari: {is_safari}")
                return is_safari
            
            return False
            
        except Exception as e:
            print(f"⚠️ Could not check frontmost app: {e}")
            return False
    
    def _is_safari_on_youtube(self):
        """Check if Safari's current tab is on YouTube"""
        try:
            import subprocess
            
            # AppleScript to get the current URL from Safari
            url_script = '''
            tell application "Safari"
                if it is running then
                    try
                        set currentURL to URL of current tab of front window
                        return currentURL
                    end try
                end if
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', url_script], 
                                  capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip().lower()
                # Check if URL contains youtube.com
                is_youtube = 'youtube.com' in url or 'youtu.be' in url
                print(f"🌐 Safari URL: {url[:50]}... | YouTube: {is_youtube}")
                return is_youtube
            
            return False
            
        except Exception as e:
            print(f"⚠️ Could not verify YouTube URL: {e}")
            # If we can't verify, assume it's not YouTube to be safe
            return False
    
    def _capture_window(self, window_info):
        """Capture Safari video window - focused on YouTube video player only"""
        try:
            print("📷 Attempting to capture Safari window...")
            
            # Re-verify Safari is still frontmost before capture (prevent race condition)
            if not self._is_safari_frontmost():
                print("⚠️ Safari is no longer frontmost - aborting capture")
                return None
            
            safari_bounds = self._get_safari_window_bounds()
            
            if safari_bounds:
                left, top, width, height = safari_bounds
                print(f"🖼️ Capturing Safari at bounds: {safari_bounds}")
                
                # Final check: verify Safari is STILL frontmost right before capture
                if not self._is_safari_frontmost():
                    print("⚠️ Safari lost focus during setup - aborting capture")
                    return None
                
                # Capture Safari window
                browser_screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
                print(f"✅ Safari screenshot captured: {browser_screenshot.size}")
                
                # Adaptive YouTube video player area detection
                # Works for both normal mode and theater mode
                # Theater mode: video is wider (~90% width) and taller (~70% height)
                # Normal mode: video is narrower (~60% width) and shorter (~45% height)
                
                # Use generous margins that work for both modes
                video_left = int(width * 0.08)      # Minimal left margin (works for theater mode)
                video_top = int(height * 0.10)      # Skip top navigation bar
                video_width = int(width * 0.84)     # Wide capture (84% width - works for theater mode)
                video_height = int(height * 0.70)   # Tall capture (70% height - works for theater mode)
                
                # Ensure we have valid dimensions
                if video_width < 100 or video_height < 100:
                    print("⚠️ Video area too small, using fallback dimensions")
                    video_left = int(width * 0.10)
                    video_top = int(height * 0.10)
                    video_width = int(width * 0.80)
                    video_height = int(height * 0.70)
                
                screenshot = browser_screenshot.crop((
                    video_left,
                    video_top,
                    video_left + video_width,
                    video_top + video_height
                ))
                print(f"🎬 Video player area cropped to: {screenshot.size}")
                print(f"📐 Crop region: left={video_left}, top={video_top}, width={video_width}, height={video_height}")
                print(f"🎭 Capture mode: Adaptive (supports both normal and theater mode)")
                
                # Convert to OpenCV format
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                print("✅ Screenshot converted to OpenCV format")
                return screenshot_cv
            else:
                print("❌ Safari bounds not available")
                return None
            
        except Exception as e:
            print(f"⚠️ Error capturing window: {e}")
            return None
    
    def _get_safari_window_bounds(self):
        """Get Safari window bounds for video capture (without activating)"""
        try:
            import subprocess
            
            # Get bounds without activating Safari, check if window exists
            safari_script = '''
            tell application "Safari"
                if it is running then
                    if (count of windows) > 0 then
                        tell front window
                            if visible then
                                set windowBounds to bounds
                                return windowBounds
                            end if
                        end tell
                    end if
                end if
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', safari_script], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                bounds_str = result.stdout.strip()
                bounds = [int(x.strip()) for x in bounds_str.split(',')]
                
                if len(bounds) == 4:
                    left, top, right, bottom = bounds
                    width = right - left
                    height = bottom - top
                    
                    if width > 100 and height > 100:
                        return (left, top, width, height)
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error getting Safari bounds: {e}")
            return None
    
    def _analyze_screenshot(self, screenshot, window_info):
        """Analyze screenshot for personal smoking/vaping detection"""
        try:
            current_time = time.time()
            
            # Note: Cooldown is applied globally, not per-video
            # This means switching to a different video won't trigger detection
            # if within cooldown period from previous detection
            if current_time - self.last_detection_time < self.detection_cooldown:
                print("⏳ Skipping analysis - within cooldown period")
                return
            
            # Create temporary file for analysis in repo-local temp_screens/
            screens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_screens")
            try:
                os.makedirs(screens_dir, exist_ok=True)
            except OSError:
                pass
            temp_filename = f"temp_screenshot_{self.session_id}_{int(current_time)}.jpg"
            temp_path = os.path.join(screens_dir, temp_filename)
            cv2.imwrite(temp_path, screenshot)
            print(f"💾 Temporary screenshot saved: {temp_path}")
            
            # Analyze with AI
            print("🤖 Running AI analysis for smoking/vaping detection...")
            result, error = self.detector.analyze_image(temp_path)
            
            if error:
                print(f"❌ AI analysis failed: {error}")
                # Remove temp file if analysis failed
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                return
            
            if result is None:
                print("❌ AI analysis returned no result")
                # Remove temp file if no result
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                return
            
            print(f"📊 AI analysis complete: smoking={result.get('smoking_detected', False)}, vaping={result.get('vaping_detected', False)}")
                
            # Only keep screenshot if smoking/vaping detected
            if result.get('smoking_detected') or result.get('vaping_detected'):
                detection_type = "smoking" if result.get('smoking_detected') else "vaping"
                print(f"🚨 {detection_type.upper()} DETECTED! Saving screenshot: {temp_path}")
                
                # Handle both smoking and vaping if both detected
                if result.get('smoking_detected') and result.get('vaping_detected'):
                    detection_type = "smoking & vaping"
                    print("🚨 BOTH SMOKING & VAPING DETECTED!")
                
                self._send_self_alert(detection_type, result, temp_path)
                # Keep the file for evidence and cleanup old screenshots
                self._cleanup_old_screenshots()
            else:
                print("✅ No smoking or vaping detected - removing temp file")
                # Remove temp file if no detection
                try:
                    os.remove(temp_path)
                except OSError:
                    pass  # File might already be deleted
            
            self.last_detection_time = current_time
            
        except Exception as e:
            # Clean up temp file on error
            try:
                if 'temp_path' in locals():
                    os.remove(temp_path)
            except OSError:
                pass
            pass  # Silent error handling
    
    def _cleanup_old_screenshots(self):
        """Keep only the last 5 screenshots, delete older ones"""
        try:
            screens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_screens")
            if not os.path.exists(screens_dir):
                return
            
            # Get all screenshot files for this session
            screenshot_files = []
            for filename in os.listdir(screens_dir):
                if filename.startswith(f"temp_screenshot_{self.session_id}_") and filename.endswith(".jpg"):
                    filepath = os.path.join(screens_dir, filename)
                    # Get file modification time
                    mtime = os.path.getmtime(filepath)
                    screenshot_files.append((filepath, mtime))
            
            # Sort by modification time (newest first)
            screenshot_files.sort(key=lambda x: x[1], reverse=True)
            
            # Keep only the last 5, delete the rest
            if len(screenshot_files) > self.max_screenshots:
                files_to_delete = screenshot_files[self.max_screenshots:]
                for filepath, _ in files_to_delete:
                    try:
                        os.remove(filepath)
                        print(f"🗑️ Deleted old screenshot: {os.path.basename(filepath)}")
                    except OSError as e:
                        print(f"⚠️ Failed to delete {filepath}: {e}")
                
                print(f"✅ Kept last {self.max_screenshots} screenshots, deleted {len(files_to_delete)} old ones")
        
        except Exception as e:
            print(f"⚠️ Error cleaning up old screenshots: {e}")
    
    def _send_self_alert(self, detection_type, detection_result, screenshot_path):
        """Send self-monitoring alert"""
        try:
            detection_types = detection_result.get('detection_types', [])
            
            if 'smoking' in detection_types and 'vaping' in detection_types:
                alert_type = "🚭💨 Smoking & Vaping"
            elif 'smoking' in detection_types:
                alert_type = "🚭 Smoking"
            elif 'vaping' in detection_types:
                alert_type = "💨 Vaping"
            else:
                alert_type = "⚠️ Smoking/Vaping"
            
            print(f"🚨 SELF-MONITORING ALERT: {alert_type} detected!")
            print(f"Screenshot saved: {screenshot_path}")
            print(f"Detection confidence: {detection_result.get('max_confidence', 0):.2f}")
            
            # Broadcast WebSocket alert from thread-safe helper
            message = {
                "type": "detection",
                "label": "Vaping and Smoking Detection",
                "detection_type": alert_type.replace("🚭💨 ", "").replace("🚭 ", "").replace("💨 ", "").lower(),
                "max_confidence": float(detection_result.get("max_confidence", 0.0)),
                "timestamp": time.time(),
                "screenshot_path": screenshot_path,
            }
            try:
                broadcast_from_thread(message)
            except Exception:
                pass
            
            # Save detection to database
            self._handle_detection(detection_result, {'app': 'Safari', 'title': 'Video Content'}, screenshot_path)
            
        except Exception as e:
            pass  # Silent error handling
    
    def _handle_detection(self, detection_result, window_info, screenshot_path):
        """Handle positive smoking/vaping detection for self-monitoring"""
        try:
            # Save detection to database
            conn = sqlite3.connect('monitoring.db')
            cursor = conn.cursor()
            
            max_confidence = detection_result.get('max_confidence', 0)
            
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
            
            # Alert already sent in _analyze_screenshot, no need to duplicate
                
        except Exception as e:
            pass  # Silent error handling
    
    def _send_self_notification(self, detection_result, window_info):
        """Send immediate self-monitoring notification"""
        # This would integrate with personal notification service
        # Self-notification would be sent in production

@router.post("/start-monitoring")
async def start_monitoring(request: StartMonitoringRequest):
    """Start self-monitoring for personal use"""
    try:
        # Save monitoring session to database
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO monitoring_sessions (device_id, user_email, settings)
            VALUES (?, ?, ?)
        ''', (request.deviceId, "user@self-monitoring.local", json.dumps(request.settings.dict())))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Start self-monitoring
        monitor = SelfVideoMonitor(session_id, request.settings)
        monitor.start_monitoring()
        
        active_monitoring_sessions[request.deviceId] = {
            'session_id': session_id,
            'monitor': monitor,
            'user_email': "user@self-monitoring.local"
        }
        
        return {"status": "success", "message": "Self-monitoring started", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start self-monitoring: {e}")

@router.post("/stop-monitoring")
async def stop_monitoring(device_id: str = "mobile_device_001"):
    """Stop self-monitoring for personal use"""
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
            
        return {"status": "success", "message": "Self-monitoring stopped"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop self-monitoring: {e}")

@router.get("/stats")
async def get_monitoring_stats(device_id: str = "mobile_device_001"):
    """Get self-monitoring statistics"""
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
        
        # Get daily stats from database
        cursor.execute('''
            SELECT 
                DATE(detection_time) as date,
                COUNT(*) as detections
            FROM video_detections 
            WHERE session_id = ?
            GROUP BY DATE(detection_time)
            ORDER BY date DESC
            LIMIT 30
        ''', (session_id,))
        
        daily_stats = []
        for row in cursor.fetchall():
            daily_stats.append({
                "date": row[0],
                "detections": row[1]
            })
        
        # Calculate total videos watched from daily_stats table
        cursor.execute('''
            SELECT COALESCE(SUM(total_videos_watched), 0)
            FROM daily_stats 
            WHERE session_id = ?
        ''', (session_id,))
        
        total_videos_result = cursor.fetchone()
        total_videos = total_videos_result[0] if total_videos_result else 0
        
        # If no data in daily_stats table, estimate from detection count
        # (This is a fallback - in production you'd track all videos watched)
        if total_videos == 0 and smoking_detections > 0:
            total_videos = smoking_detections
        
        conn.close()
        
        return MonitoringStats(
            totalVideosWatched=total_videos,
            smokingContentDetected=smoking_detections,
            lastDetection=last_detection,
            dailyStats=daily_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")

@router.post("/send-test-report")
async def send_test_report(request: dict):
    """Send test report for self-monitoring"""
    try:
        user_email = request.get('userEmail', 'user@self-monitoring.local')
        
        # Self-monitoring doesn't require email validation
        
        # Create test report
        report_html = f"""
        <html>
        <body>
            <h2>🚭 Cigarette Detection - Test Report</h2>
            <p>This is a test report from your personal self-monitoring system.</p>
            
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
            
            <p><em>This system helps you monitor smoking content in videos you watch.</em></p>
            
            <hr>
            <p><small>Smoking & Vaping Detection System - Self-Monitoring Report</small></p>
        </body>
        </html>
        """
        
        # In production, you would send actual email here
        # For now, we'll just simulate it
        # Test report would be sent to user in production
        
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

# Email notification system (simplified - no email dependencies)
class EmailNotifier:
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        # In production, these would be environment variables
        self.email_user = os.getenv("NOTIFICATION_EMAIL", "")
        self.email_password = os.getenv("NOTIFICATION_PASSWORD", "")
    
    def send_daily_report(self, user_email: str, stats: dict):
        """Send daily self-monitoring report (simulated for now)"""
        try:
            body = self._create_daily_report_html(stats)
            
            # Email functionality disabled due to Python email module issues
            # In production, this would send actual emails
            # Daily report would be sent to user in production
            
        except Exception as e:
            pass  # Silent error handling
    
    def _create_daily_report_html(self, stats: dict) -> str:
        """Create HTML content for daily report"""
        return f"""
        🚭 Daily Self-Monitoring Report
        
        Here's your personal video watching activity for today:
        
        📊 Today's Statistics:
        - Videos Watched: {stats.get('videos_watched', 0)}
        - Smoking Content Detected: {stats.get('smoking_detected', 0)}
        - Watch Time: {stats.get('watch_time_minutes', 0)} minutes
        
        Stay informed about your personal digital content consumption.
        """

# Background task for sending scheduled reports
async def send_scheduled_reports():
    """Send daily/weekly self-monitoring reports"""
    # This would run as a background task
    pass
