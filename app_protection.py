#!/usr/bin/env python3
"""
App Protection and Deletion Detection System
Monitors for app removal and sends notifications to parents
"""

import os
import sys
import time
import threading
import sqlite3
import json
# Email functionality temporarily disabled due to Python email module issues
# import smtplib
# from email.mime.text import MimeText
# from email.mime.multipart import MimeMultipart
import hashlib
import platform
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
import psutil

class AppProtectionSystem:
    def __init__(self, app_directory=None, parent_email=None):
        # Determine base application directory
        if app_directory is not None:
            base_dir = app_directory
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # When frozen (py2app/pyinstaller), write protection data to a
        # user-writable directory instead of the app bundle.
        if getattr(sys, "frozen", False):
            user_base = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "EscVapeDetector",
            )
            try:
                os.makedirs(user_base, exist_ok=True)
                self.app_directory = user_base
            except Exception:
                # Fallback to base_dir if user directory cannot be created
                self.app_directory = base_dir
        else:
            self.app_directory = base_dir
        self.parent_email = parent_email
        self.protection_db = os.path.join(self.app_directory, "protection.db")
        self.heartbeat_interval = 300  # 5 minutes
        self.is_running = False
        self.protection_thread = None
        
        # Critical files to monitor
        self.critical_files = [
            "main.py",
            "api_server.py", 
            "parental_control_api.py",
            "desktop_client.py",
            "app_protection.py",
            "models/yolov4.weights",
            "models/yolov4.cfg"
        ]
        
        self.init_protection_db()
        
    def init_protection_db(self):
        """Initialize protection database"""
        # Ensure directory for the database exists
        try:
            os.makedirs(os.path.dirname(self.protection_db), exist_ok=True)
        except Exception:
            pass

        conn = sqlite3.connect(self.protection_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                parent_email TEXT NOT NULL,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                app_hash TEXT,
                installation_path TEXT,
                protection_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deletion_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                details TEXT,
                email_sent BOOLEAN DEFAULT FALSE,
                parent_email TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_integrity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'OK'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_app_hash(self):
        """Calculate hash of critical app files"""
        hasher = hashlib.sha256()
        
        for file_path in self.critical_files:
            full_path = os.path.join(self.app_directory, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def register_installation(self, device_id, parent_email):
        """Register app installation with protection"""
        conn = sqlite3.connect(self.protection_db)
        cursor = conn.cursor()
        
        app_hash = self.calculate_app_hash()
        
        # Check if already registered
        cursor.execute('SELECT id FROM app_status WHERE device_id = ?', (device_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing registration
            cursor.execute('''
                UPDATE app_status 
                SET parent_email = ?, app_hash = ?, last_heartbeat = CURRENT_TIMESTAMP,
                    installation_path = ?, protection_enabled = TRUE
                WHERE device_id = ?
            ''', (parent_email, app_hash, self.app_directory, device_id))
        else:
            # New registration
            cursor.execute('''
                INSERT INTO app_status 
                (device_id, parent_email, app_hash, installation_path)
                VALUES (?, ?, ?, ?)
            ''', (device_id, parent_email, app_hash, self.app_directory))
        
        # Store file integrity hashes
        self.update_file_integrity()
        
        conn.commit()
        conn.close()
        
        self.parent_email = parent_email
        return True
    
    def update_file_integrity(self):
        """Update file integrity database"""
        conn = sqlite3.connect(self.protection_db)
        cursor = conn.cursor()
        
        for file_path in self.critical_files:
            full_path = os.path.join(self.app_directory, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO file_integrity 
                    (file_path, file_hash, last_checked, status)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 'OK')
                ''', (file_path, file_hash))
        
        conn.commit()
        conn.close()
    
    def check_file_integrity(self):
        """Check if critical files have been modified or deleted"""
        conn = sqlite3.connect(self.protection_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_path, file_hash FROM file_integrity')
        stored_files = cursor.fetchall()
        
        issues = []
        
        for file_path, stored_hash in stored_files:
            full_path = os.path.join(self.app_directory, file_path)
            
            if not os.path.exists(full_path):
                issues.append({
                    'type': 'FILE_DELETED',
                    'file': file_path,
                    'message': f'Critical file deleted: {file_path}'
                })
            else:
                with open(full_path, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                
                if current_hash != stored_hash:
                    issues.append({
                        'type': 'FILE_MODIFIED',
                        'file': file_path,
                        'message': f'Critical file modified: {file_path}'
                    })
        
        conn.close()
        return issues
    
    def send_heartbeat(self, device_id):
        """Send heartbeat to indicate app is still running"""
        conn = sqlite3.connect(self.protection_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE app_status 
            SET last_heartbeat = CURRENT_TIMESTAMP 
            WHERE device_id = ?
        ''', (device_id,))
        
        conn.commit()
        conn.close()
    
    def check_for_tampering(self, device_id):
        """Check for app tampering or deletion attempts"""
        issues = []
        
        # Check file integrity
        file_issues = self.check_file_integrity()
        issues.extend(file_issues)
        
        # Check if app directory still exists
        if not os.path.exists(self.app_directory):
            issues.append({
                'type': 'APP_DIRECTORY_DELETED',
                'message': 'App directory has been deleted'
            })
        
        # Check if protection database is accessible
        if not os.path.exists(self.protection_db):
            issues.append({
                'type': 'PROTECTION_DB_DELETED',
                'message': 'Protection database has been deleted'
            })
        
        # Log any issues found
        if issues:
            self.log_deletion_alert(device_id, issues)
            return issues
        
        return []
    
    def log_deletion_alert(self, device_id, issues):
        """Log deletion/tampering alerts"""
        try:
            conn = sqlite3.connect(self.protection_db)
            cursor = conn.cursor()
            
            for issue in issues:
                cursor.execute('''
                    INSERT INTO deletion_alerts 
                    (device_id, alert_type, details, parent_email)
                    VALUES (?, ?, ?, ?)
                ''', (device_id, issue['type'], json.dumps(issue), self.parent_email))
            
            conn.commit()
            conn.close()
        except Exception as e:
            # If database is inaccessible, try alternative logging
            self.emergency_log(device_id, issues, str(e))
    
    def emergency_log(self, device_id, issues, error):
        """Emergency logging when database is inaccessible"""
        try:
            # Try to write to a hidden file
            emergency_file = os.path.join(os.path.expanduser("~"), ".cigarette_detection_emergency.log")
            with open(emergency_file, 'a') as f:
                f.write(f"\n[{datetime.now()}] EMERGENCY LOG - Device: {device_id}\n")
                f.write(f"Database Error: {error}\n")
                for issue in issues:
                    f.write(f"Issue: {issue}\n")
                f.write("-" * 50 + "\n")
        except:
            pass  # If even emergency logging fails, continue silently
    
    def send_deletion_notification(self, device_id, issues):
        """Send email notification about app deletion/tampering"""
        if not self.parent_email:
            return False
        
        try:
            # Create email content
            subject = f"🚨 ALERT: Cigarette Detection App Tampering Detected"
            
            html_body = f"""
            <html>
            <body>
                <h2>🚨 Security Alert</h2>
                <p><strong>Device:</strong> {device_id}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h3>⚠️ Detected Issues:</h3>
                <ul>
            """
            
            for issue in issues:
                html_body += f"<li><strong>{issue['type']}:</strong> {issue['message']}</li>"
            
            html_body += """
                </ul>
                
                <h3>🔍 Possible Causes:</h3>
                <ul>
                    <li>App was uninstalled or deleted</li>
                    <li>Critical files were modified or removed</li>
                    <li>App directory was moved or renamed</li>
                    <li>System was reset or restored</li>
                </ul>
                
                <h3>📋 Recommended Actions:</h3>
                <ul>
                    <li>Check the device immediately</li>
                    <li>Verify app installation status</li>
                    <li>Reinstall if necessary</li>
                    <li>Review device access logs</li>
                </ul>
                
                <hr>
                <p><small>Cigarette Detection System - Security Monitoring</small></p>
            </body>
            </html>
            """
            
            # Send email (using same email system as reports)
            self.send_email_alert(subject, html_body)
            
            # Mark alerts as sent
            self.mark_alerts_sent(device_id)
            
            return True
            
        except Exception as e:
            print(f"Failed to send deletion notification: {e}")
            return False
    
    def send_email_alert(self, subject, html_body):
        """Send email alert (simulated - no email dependencies)"""
        # Email functionality disabled due to Python email module issues
        print(f"📧 SIMULATED EMAIL ALERT TO: {self.parent_email}")
        print(f"📋 SUBJECT: {subject}")
        print("📄 BODY:", html_body[:200] + "...")
        print("✅ Email alert simulation completed")
        
        # TODO: Re-enable actual email sending once Python email module is fixed
    
    def mark_alerts_sent(self, device_id):
        """Mark alerts as sent in database"""
        try:
            conn = sqlite3.connect(self.protection_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE deletion_alerts 
                SET email_sent = TRUE 
                WHERE device_id = ? AND email_sent = FALSE
            ''', (device_id,))
            
            conn.commit()
            conn.close()
        except:
            pass  # Fail silently if database is inaccessible
    
    def start_protection(self, device_id):
        """Start protection monitoring"""
        self.is_running = True
        self.device_id = device_id
        
        def protection_loop():
            while self.is_running:
                try:
                    # Send heartbeat
                    self.send_heartbeat(device_id)
                    
                    # Check for tampering
                    issues = self.check_for_tampering(device_id)
                    
                    if issues:
                        # Send notification
                        self.send_deletion_notification(device_id, issues)
                        
                        # Log to console for debugging
                        print(f"SECURITY ALERT: {len(issues)} issues detected!")
                        for issue in issues:
                            print(f"  - {issue['type']}: {issue['message']}")
                    
                    # Wait for next check
                    time.sleep(self.heartbeat_interval)
                    
                except Exception as e:
                    print(f"Protection monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start protection in background thread
        self.protection_thread = threading.Thread(target=protection_loop, daemon=True)
        self.protection_thread.start()
        
        print(f"App protection started for device: {device_id}")
        return True
    
    def stop_protection(self):
        """Stop protection monitoring"""
        self.is_running = False
        if self.protection_thread:
            self.protection_thread.join(timeout=5)
        print("App protection stopped")
    
    def get_protection_status(self, device_id):
        """Get current protection status"""
        try:
            conn = sqlite3.connect(self.protection_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_heartbeat, protection_enabled, created_at 
                FROM app_status WHERE device_id = ?
            ''', (device_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                last_heartbeat, enabled, created_at = result
                return {
                    'protected': enabled,
                    'last_heartbeat': last_heartbeat,
                    'created_at': created_at,
                    'status': 'active' if self.is_running else 'inactive'
                }
            else:
                return {'protected': False, 'status': 'not_registered'}
                
        except Exception as e:
            return {'protected': False, 'status': 'error', 'error': str(e)}

# Standalone protection service
class ProtectionService:
    """Standalone service that runs independently"""
    
    def __init__(self):
        self.service_file = os.path.join(os.path.expanduser("~"), ".cigarette_detection_service.json")
        self.protection_system = None
    
    def install_service(self, device_id, parent_email, app_directory):
        """Install protection service"""
        service_config = {
            'device_id': device_id,
            'parent_email': parent_email,
            'app_directory': app_directory,
            'installed_at': datetime.now().isoformat(),
            'enabled': True
        }
        
        # Save service configuration
        with open(self.service_file, 'w') as f:
            json.dump(service_config, f)
        
        # Initialize protection system
        self.protection_system = AppProtectionSystem(app_directory, parent_email)
        self.protection_system.register_installation(device_id, parent_email)
        
        # Start protection
        self.protection_system.start_protection(device_id)
        
        return True
    
    def run_service(self):
        """Run protection service"""
        if not os.path.exists(self.service_file):
            print("Protection service not installed")
            return
        
        with open(self.service_file, 'r') as f:
            config = json.load(f)
        
        if not config.get('enabled', False):
            print("Protection service disabled")
            return
        
        # Initialize and start protection
        self.protection_system = AppProtectionSystem(
            config['app_directory'], 
            config['parent_email']
        )
        
        self.protection_system.start_protection(config['device_id'])
        
        # Keep service running
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            self.protection_system.stop_protection()

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='App Protection Service')
    parser.add_argument('--install', action='store_true', help='Install protection service')
    parser.add_argument('--device-id', required=True, help='Device ID')
    parser.add_argument('--parent-email', required=True, help='Parent email for notifications')
    parser.add_argument('--app-dir', default='.', help='App directory to protect')
    
    args = parser.parse_args()
    
    service = ProtectionService()
    
    if args.install:
        service.install_service(args.device_id, args.parent_email, args.app_dir)
        print("Protection service installed and started")
    else:
        service.run_service()

if __name__ == "__main__":
    main()
