#!/usr/bin/env python3
"""
Desktop GUI Client for Vaping and Smoking Detection System
Includes image detection, parental control, and app protection features
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import json
import os
from PIL import Image, ImageTk
import threading
import time

class CigaretteDetectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vaping and Smoking Detection System")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"900x700+{x}+{y}")
        
        # API configuration
        self.api_base_url = "http://localhost:8000"
        
        # Variables
        self.monitoring_active = tk.BooleanVar()
        self.protection_enabled = tk.BooleanVar()
        
        # Force window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        self.setup_ui()
        self.check_api_connection()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Vaping and Smoking Detection System", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # Tab 1: Image Detection
        self.detection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.detection_frame, text="🔍 Image Detection")
        self.setup_detection_tab()
        
        # Tab 2: Parental Control
        self.parental_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.parental_frame, text="👨‍👩‍👧‍👦 Parental Control")
        self.setup_parental_tab()
        
        # Tab 3: Monitoring Stats
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="📊 Monitoring Stats")
        self.setup_stats_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("✅ Ready - API Connection: Checking...")
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                                   relief=tk.SUNKEN, padding=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Force update
        self.root.update_idletasks()
        print("✅ GUI setup completed")
    
    def setup_detection_tab(self):
        """Setup image detection tab"""
        print("🔍 Setting up detection tab...")
        
        # Create scrollable frame
        canvas = tk.Canvas(self.detection_frame)
        scrollbar = ttk.Scrollbar(self.detection_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title_label = ttk.Label(scrollable_frame, text="🔍 Vaping and Smoking Detection", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Test label to verify content is showing
        test_label = ttk.Label(scrollable_frame, text="Detection tab loaded successfully!", 
                              foreground="green")
        test_label.pack(pady=5)
        
        # File selection
        file_frame = ttk.Frame(self.detection_frame)
        file_frame.pack(pady=10, fill="x", padx=20)
        
        ttk.Label(file_frame, text="Select Image:").pack(anchor="w")
        
        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.pack(fill="x", pady=5)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_select_frame, textvariable=self.file_path_var, state="readonly")
        file_entry.pack(side="left", fill="x", expand=True)
        
        browse_btn = ttk.Button(file_select_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side="right", padx=(5, 0))
        
        # Confidence threshold
        conf_frame = ttk.Frame(self.detection_frame)
        conf_frame.pack(pady=10, fill="x", padx=20)
        
        ttk.Label(conf_frame, text="Confidence Threshold:").pack(anchor="w")
        self.confidence_var = tk.DoubleVar(value=0.5)
        conf_scale = ttk.Scale(conf_frame, from_=0.1, to=1.0, variable=self.confidence_var, orient="horizontal")
        conf_scale.pack(fill="x", pady=5)
        
        conf_label = ttk.Label(conf_frame, text="0.5")
        conf_label.pack()
        
        def update_conf_label(*args):
            conf_label.config(text=f"{self.confidence_var.get():.2f}")
        self.confidence_var.trace("w", update_conf_label)
        
        # Analyze button
        analyze_btn = ttk.Button(self.detection_frame, text="Analyze Image", command=self.analyze_image)
        analyze_btn.pack(pady=20)
        
        # Results area
        results_frame = ttk.LabelFrame(self.detection_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Results text
        self.results_text = tk.Text(results_frame, height=10, wrap="word")
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_parental_tab(self):
        """Setup parental control tab"""
        # Title
        title_label = ttk.Label(self.parental_frame, text="Parental Control & Monitoring", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Configuration section
        config_frame = ttk.LabelFrame(self.parental_frame, text="Configuration")
        config_frame.pack(fill="x", padx=20, pady=10)
        
        # Parent email
        email_frame = ttk.Frame(config_frame)
        email_frame.pack(fill="x", pady=5)
        ttk.Label(email_frame, text="Parent Email:").pack(side="left")
        self.parent_email_var = tk.StringVar()
        email_entry = ttk.Entry(email_frame, textvariable=self.parent_email_var, width=30)
        email_entry.pack(side="right")
        
        # Device ID
        device_frame = ttk.Frame(config_frame)
        device_frame.pack(fill="x", pady=5)
        ttk.Label(device_frame, text="Device ID:").pack(side="left")
        self.device_id_var = tk.StringVar(value="desktop_device_001")
        device_entry = ttk.Entry(device_frame, textvariable=self.device_id_var, width=30)
        device_entry.pack(side="right")
        
        # Monitoring settings
        settings_frame = ttk.LabelFrame(self.parental_frame, text="Monitoring Settings")
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # Real-time alerts
        self.realtime_alerts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Real-time Alerts", variable=self.realtime_alerts_var).pack(anchor="w")
        
        # Daily reports
        self.daily_reports_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Daily Reports", variable=self.daily_reports_var).pack(anchor="w")
        
        # Sensitivity level
        sens_frame = ttk.Frame(settings_frame)
        sens_frame.pack(fill="x", pady=5)
        ttk.Label(sens_frame, text="Sensitivity Level:").pack(side="left")
        self.sensitivity_var = tk.StringVar(value="medium")
        sens_combo = ttk.Combobox(sens_frame, textvariable=self.sensitivity_var, 
                                 values=["low", "medium", "high"], state="readonly")
        sens_combo.pack(side="right")
        
        # Monitoring controls
        control_frame = ttk.LabelFrame(self.parental_frame, text="Monitoring Control")
        control_frame.pack(fill="x", padx=20, pady=10)
        
        # Status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill="x", pady=5)
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.monitoring_status_label = ttk.Label(status_frame, text="Inactive", foreground="red")
        self.monitoring_status_label.pack(side="right")
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(pady=10)
        
        self.start_monitoring_btn = ttk.Button(btn_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_monitoring_btn.pack(side="left", padx=5)
        
        self.stop_monitoring_btn = ttk.Button(btn_frame, text="Stop Monitoring", command=self.stop_monitoring, state="disabled")
        self.stop_monitoring_btn.pack(side="left", padx=5)
        
        # Test report button
        test_report_btn = ttk.Button(btn_frame, text="Send Test Report", command=self.send_test_report)
        test_report_btn.pack(side="left", padx=5)
        
        # App Protection section
        protection_frame = ttk.LabelFrame(self.parental_frame, text="App Protection")
        protection_frame.pack(fill="x", padx=20, pady=10)
        
        # Protection status
        prot_status_frame = ttk.Frame(protection_frame)
        prot_status_frame.pack(fill="x", pady=5)
        ttk.Label(prot_status_frame, text="Protection Status:").pack(side="left")
        self.protection_status_label = ttk.Label(prot_status_frame, text="Disabled", foreground="red")
        self.protection_status_label.pack(side="right")
        
        # Protection buttons
        prot_btn_frame = ttk.Frame(protection_frame)
        prot_btn_frame.pack(pady=10)
        
        self.enable_protection_btn = ttk.Button(prot_btn_frame, text="Enable Protection", command=self.enable_protection)
        self.enable_protection_btn.pack(side="left", padx=5)
        
        self.disable_protection_btn = ttk.Button(prot_btn_frame, text="Disable Protection", command=self.disable_protection, state="disabled")
        self.disable_protection_btn.pack(side="left", padx=5)
        
        check_protection_btn = ttk.Button(prot_btn_frame, text="Check Status", command=self.check_protection_status)
        check_protection_btn.pack(side="left", padx=5)
    
    def setup_stats_tab(self):
        """Setup monitoring statistics tab"""
        # Title
        title_label = ttk.Label(self.stats_frame, text="Monitoring Statistics", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Stats display
        stats_display_frame = ttk.LabelFrame(self.stats_frame, text="Current Statistics")
        stats_display_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create stats labels
        self.stats_labels = {}
        
        stats_items = [
            ("Total Videos Watched", "totalVideosWatched"),
            ("Smoking Content Detected", "smokingContentDetected"),
            ("Last Detection", "lastDetection"),
            ("Detection Rate", "detectionRate")
        ]
        
        for i, (label_text, key) in enumerate(stats_items):
            frame = ttk.Frame(stats_display_frame)
            frame.pack(fill="x", pady=5, padx=10)
            
            ttk.Label(frame, text=f"{label_text}:", font=("Arial", 10, "bold")).pack(side="left")
            value_label = ttk.Label(frame, text="--")
            value_label.pack(side="right")
            
            self.stats_labels[key] = value_label
        
        # Refresh button
        refresh_btn = ttk.Button(self.stats_frame, text="Refresh Statistics", command=self.refresh_stats)
        refresh_btn.pack(pady=10)
        
        # Auto-refresh
        self.auto_refresh_stats()
    
    def check_api_connection(self):
        """Check if API server is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                self.status_var.set("Connected to API server")
            else:
                self.status_var.set("API server error")
        except requests.exceptions.RequestException:
            self.status_var.set("API server not available - Please start the server")
    
    def browse_file(self):
        """Browse for image file"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def analyze_image(self):
        """Analyze selected image"""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("Error", "Please select an image file")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Selected file does not exist")
            return
        
        self.status_var.set("Analyzing image...")
        self.results_text.delete(1.0, tk.END)
        
        def analyze():
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    data = {'confidence_threshold': self.confidence_var.get()}
                    
                    response = requests.post(
                        f"{self.api_base_url}/detect/single",
                        files=files,
                        data=data,
                        timeout=30
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    self.display_results(result)
                    self.status_var.set("Analysis complete")
                else:
                    error_msg = f"API Error: {response.status_code}"
                    self.results_text.insert(tk.END, error_msg)
                    self.status_var.set("Analysis failed")
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Connection Error: {str(e)}"
                self.results_text.insert(tk.END, error_msg)
                self.status_var.set("Connection failed")
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.results_text.insert(tk.END, error_msg)
                self.status_var.set("Analysis failed")
        
        # Run analysis in background thread
        threading.Thread(target=analyze, daemon=True).start()
    
    def display_results(self, result):
        """Display analysis results"""
        self.results_text.delete(1.0, tk.END)
        
        # Main result
        cigarette_detected = result.get('cigarette_detected', False)
        max_confidence = result.get('max_confidence', 0)
        
        self.results_text.insert(tk.END, f"SMOKING DETECTION RESULTS (vaping devices and cigarettes)\n")
        self.results_text.insert(tk.END, "=" * 40 + "\n\n")
        
        if cigarette_detected:
            self.results_text.insert(tk.END, "🚨 CIGARETTE DETECTED!\n", "alert")
            self.results_text.insert(tk.END, f"Max Confidence: {max_confidence:.2f}\n\n")
        else:
            self.results_text.insert(tk.END, "✅ No cigarette detected\n\n")
        
        # Detailed detections
        detections = result.get('detections', [])
        if detections:
            self.results_text.insert(tk.END, f"Detailed Detections ({len(detections)} objects):\n")
            self.results_text.insert(tk.END, "-" * 30 + "\n")
            
            for i, detection in enumerate(detections, 1):
                class_name = detection.get('class', 'unknown')
                confidence = detection.get('confidence', 0)
                is_cigarette = detection.get('is_cigarette_related', False)
                
                line = f"{i}. {class_name} (confidence: {confidence:.2f})"
                if is_cigarette:
                    line += " [CIGARETTE-RELATED]"
                line += "\n"
                
                self.results_text.insert(tk.END, line)
        
        # Analysis info
        analysis_time = result.get('analysis_time', 0)
        self.results_text.insert(tk.END, f"\nAnalysis Time: {analysis_time:.2f} seconds")
        
        # Configure text tags for styling
        self.results_text.tag_configure("alert", foreground="red", font=("Arial", 12, "bold"))
    
    def start_monitoring(self):
        """Start video monitoring"""
        parent_email = self.parent_email_var.get().strip()
        device_id = self.device_id_var.get().strip()
        
        if not parent_email:
            messagebox.showerror("Error", "Please enter parent email")
            return
        
        if not device_id:
            messagebox.showerror("Error", "Please enter device ID")
            return
        
        def start():
            try:
                data = {
                    "parentEmail": parent_email,
                    "deviceId": device_id,
                    "settings": {
                        "realTimeAlerts": self.realtime_alerts_var.get(),
                        "dailyReports": self.daily_reports_var.get(),
                        "weeklyReports": False,
                        "sensitivityLevel": self.sensitivity_var.get(),
                        "monitoredApps": ["youtube", "tiktok", "instagram", "netflix"]
                    }
                }
                
                response = requests.post(
                    f"{self.api_base_url}/parental-control/start-monitoring",
                    json=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.monitoring_active.set(True)
                    self.monitoring_status_label.config(text="Active", foreground="green")
                    self.start_monitoring_btn.config(state="disabled")
                    self.stop_monitoring_btn.config(state="normal")
                    self.status_var.set("Monitoring started successfully")
                    messagebox.showinfo("Success", "Video monitoring started successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to start monitoring: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start monitoring: {str(e)}")
        
        threading.Thread(target=start, daemon=True).start()
    
    def stop_monitoring(self):
        """Stop video monitoring"""
        def stop():
            try:
                device_id = self.device_id_var.get().strip()
                response = requests.post(
                    f"{self.api_base_url}/parental-control/stop-monitoring",
                    params={"device_id": device_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.monitoring_active.set(False)
                    self.monitoring_status_label.config(text="Inactive", foreground="red")
                    self.start_monitoring_btn.config(state="normal")
                    self.stop_monitoring_btn.config(state="disabled")
                    self.status_var.set("Monitoring stopped")
                    messagebox.showinfo("Success", "Video monitoring stopped")
                else:
                    messagebox.showerror("Error", f"Failed to stop monitoring: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop monitoring: {str(e)}")
        
        threading.Thread(target=stop, daemon=True).start()
    
    def send_test_report(self):
        """Send test report to parent email"""
        parent_email = self.parent_email_var.get().strip()
        
        if not parent_email:
            messagebox.showerror("Error", "Please enter parent email")
            return
        
        def send():
            try:
                data = {"parentEmail": parent_email}
                response = requests.post(
                    f"{self.api_base_url}/parental-control/send-test-report",
                    json=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    messagebox.showinfo("Success", "Test report sent successfully!")
                    self.status_var.set("Test report sent")
                else:
                    messagebox.showerror("Error", f"Failed to send test report: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send test report: {str(e)}")
        
        threading.Thread(target=send, daemon=True).start()
    
    def enable_protection(self):
        """Enable app protection"""
        parent_email = self.parent_email_var.get().strip()
        device_id = self.device_id_var.get().strip()
        
        if not parent_email:
            messagebox.showerror("Error", "Please enter parent email")
            return
        
        def enable():
            try:
                data = {
                    "parentEmail": parent_email,
                    "deviceId": device_id
                }
                
                response = requests.post(
                    f"{self.api_base_url}/protection/enable",
                    json=data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.protection_enabled.set(True)
                    self.protection_status_label.config(text="Enabled", foreground="green")
                    self.enable_protection_btn.config(state="disabled")
                    self.disable_protection_btn.config(state="normal")
                    self.status_var.set("App protection enabled")
                    messagebox.showinfo("Success", "App protection enabled successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to enable protection: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to enable protection: {str(e)}")
        
        threading.Thread(target=enable, daemon=True).start()
    
    def disable_protection(self):
        """Disable app protection"""
        def disable():
            try:
                response = requests.post(
                    f"{self.api_base_url}/protection/disable",
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.protection_enabled.set(False)
                    self.protection_status_label.config(text="Disabled", foreground="red")
                    self.enable_protection_btn.config(state="normal")
                    self.disable_protection_btn.config(state="disabled")
                    self.status_var.set("App protection disabled")
                    messagebox.showinfo("Success", "App protection disabled")
                else:
                    messagebox.showerror("Error", f"Failed to disable protection: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to disable protection: {str(e)}")
        
        threading.Thread(target=disable, daemon=True).start()
    
    def check_protection_status(self):
        """Check app protection status"""
        def check():
            try:
                device_id = self.device_id_var.get().strip()
                response = requests.get(
                    f"{self.api_base_url}/protection/status",
                    params={"device_id": device_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    status = response.json()
                    protected = status.get('protected', False)
                    
                    if protected:
                        self.protection_status_label.config(text="Enabled", foreground="green")
                        self.enable_protection_btn.config(state="disabled")
                        self.disable_protection_btn.config(state="normal")
                    else:
                        self.protection_status_label.config(text="Disabled", foreground="red")
                        self.enable_protection_btn.config(state="normal")
                        self.disable_protection_btn.config(state="disabled")
                    
                    self.status_var.set(f"Protection status: {status.get('status', 'unknown')}")
                else:
                    messagebox.showerror("Error", f"Failed to check protection status: {response.text}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to check protection status: {str(e)}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def refresh_stats(self):
        """Refresh monitoring statistics"""
        def refresh():
            try:
                device_id = self.device_id_var.get().strip()
                response = requests.get(
                    f"{self.api_base_url}/parental-control/stats",
                    params={"device_id": device_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Update stats labels
                    self.stats_labels["totalVideosWatched"].config(text=str(stats.get("totalVideosWatched", 0)))
                    self.stats_labels["smokingContentDetected"].config(text=str(stats.get("smokingContentDetected", 0)))
                    self.stats_labels["lastDetection"].config(text=stats.get("lastDetection", "Never") or "Never")
                    
                    # Calculate detection rate
                    total = stats.get("totalVideosWatched", 0)
                    detected = stats.get("smokingContentDetected", 0)
                    rate = (detected / total * 100) if total > 0 else 0
                    self.stats_labels["detectionRate"].config(text=f"{rate:.1f}%")
                    
                    self.status_var.set("Statistics updated")
                else:
                    self.status_var.set("Failed to get statistics")
                    
            except Exception as e:
                self.status_var.set(f"Stats error: {str(e)}")
        
        threading.Thread(target=refresh, daemon=True).start()
    
    def auto_refresh_stats(self):
        """Auto-refresh statistics every 30 seconds"""
        self.refresh_stats()
        self.root.after(30000, self.auto_refresh_stats)  # 30 seconds

def main():
    """Main function"""
    root = tk.Tk()
    app = CigaretteDetectionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
