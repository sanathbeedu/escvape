# Vaping and Smoking Detection System

AI-powered detection of smoking in images and videos, including vaping devices and cigarettes. Includes advanced parental control features and tamper detection.

## 🌟 Features

### Core Detection
- **Image Analysis**: Detect smoking in photos (vaping devices and cigarettes) with a YOLOv4-based model
- **Batch Processing**: Analyze multiple images simultaneously
- **Apple Photos Integration**: Scan your photo library for vaping/smoking content
- **Real-time Video Monitoring**: Monitor video content (YouTube, TikTok, Instagram, Netflix) for smoking content (vaping devices and cigarettes)

### Parental Control
- **Video Content Monitoring**: Track vaping and smoking content in videos being watched
- **Real-time Alerts**: Instant notifications when smoking content is detected
- **Daily/Weekly Reports**: Comprehensive reports sent to parents via email
- **Configurable Sensitivity**: Adjustable detection sensitivity levels
- **Multi-app Support**: Monitor YouTube, TikTok, Instagram, Netflix, and more

### App Protection & Security
- **Deletion Detection**: Monitors for app removal or tampering
- **File Integrity Checking**: Detects modification of critical app files
- **Automatic Notifications**: Sends email alerts to parents when tampering is detected
- **Heartbeat System**: Continuous monitoring to ensure app is running
- **Emergency Logging**: Backup logging system for critical events

### Cross-Platform Support
- **Desktop GUI**: Full-featured desktop application (Windows, macOS, Linux)
- **Mobile App**: React Native mobile app (iOS, Android)
- **REST API**: Backend API server for all platforms
- **CLI Interface**: Command-line tools for batch processing

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Desktop GUI   │    │   Mobile App    │    │   CLI Tools     │
│  (Python/Tkinter)│    │ (React Native)  │    │   (Python)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     FastAPI Backend       │
                    │  ┌─────────────────────┐  │
                    │  │  Detection Engine   │  │
                    │  │    (YOLOv4/CV2)     │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │ Parental Control    │  │
                    │  │   Video Monitor     │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  App Protection     │  │
                    │  │ Tamper Detection    │  │
                    │  └─────────────────────┘  │
                    └───────────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     Local Storage         │
                    │ ┌─────────┐ ┌─────────┐   │
                    │ │SQLite DB│ │Model    │   │
                    │ │Jobs/Stats│ │Files    │   │
                    │ └─────────┘ └─────────┘   │
                    └───────────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd escvape

# Install Python dependencies
pip install -r requirements.txt

# Download YOLOv4 model files
python setup_models.py
```

### 2. Start the Backend API

```bash
python api_server.py
```
The API will be available at `http://localhost:8000`

### 3. Run Desktop Application

```bash
python desktop_client.py
```

### 4. Mobile App Setup

```bash
cd mobile-app
npm install
npx expo start
```

### Desktop Application

1. **Image Detection Tab**:
   - Select image file or take photo
   - Adjust confidence threshold
   - Click "Analyze Image" to detect smoking using vaping devices and cigarettes in images
   - View detailed results and detection confidence

2. **Parental Control Tab**:
   - Enter device ID (required) and parent email (optional for monitoring, required for email alerts/reports and app protection)
   - Configure monitoring settings (alerts, reports, sensitivity)
   - Start/stop video monitoring for smoking using vaping devices and cigarettes
   - Enable app protection with tamper detection (requires parent email)
   - Send test reports to verify email notifications (requires parent email)
### Mobile Application

1. **Detection Screen**:
   - Take photo or select from gallery
   - Adjust detection sensitivity for smoking using vaping devices and cigarettes
   - Get instant results with confidence scores for smoking using vaping devices and cigarettes in images

2. **Parental Control Screen**:
   - Configure parent email and monitoring settings
   - Start/stop video content monitoring
   - Send test reports to parents

3. **Statistics Screen**:
   - View monitoring statistics
   - Track daily detection trends
   - Monitor app usage patterns

### CLI Usage

```bash
# Analyze single image
python main.py --image path/to/image.jpg --confidence 0.7

# Batch process directory
python main.py --batch path/to/images/ --output results/

# Analyze Apple Photos
python main.py --apple-photos --limit 50 --output results/
```

## 🍏 macOS App Bundle (Experimental)

You can build a standalone macOS `.app` that bundles the FastAPI backend and launches the browser-based web UI using **py2app** and distribute it via a public GitHub release.

### Build the macOS App (on a Mac)

```bash
# 1. Create and activate virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download YOLOv4 model files (if not already done)
python setup_models.py

# 4. Install py2app (build tool)
pip install py2app

# 5. Build the .app bundle using setup.py
python setup.py py2app
```

After building, the macOS app will be located at:

- `dist/EscVapeDetector.app`

You can compress it for distribution:

```bash
cd dist
zip -r EscVapeDetector.zip EscVapeDetector.app
```

Upload `EscVapeDetector.zip` to a GitHub Release or any public file host so end users can download it.

### Running the Unsigned App on macOS

Because the app is not signed or notarized with an Apple Developer ID, macOS will initially block it.

End users should:

1. Download and unzip `EscVapeDetector.zip`.
2. Move `EscVapeDetector.app` to the `Applications` folder (optional but recommended).
3. First launch:
   - Double-click the app. macOS will likely show a warning about an unidentified developer.
   - Open **System Settings → Privacy & Security**.
   - In the **Security** section, click **"Open Anyway"** for `EscVapeDetector`.
   - Confirm in the dialog.

After this first approval, macOS usually allows the app to launch normally on subsequent runs.

## 🔧 Configuration

### API Configuration
- Default API endpoint: `http://localhost:8000`
- Update `API_BASE_URL` in mobile app for network access
- Configure CORS settings in `api_server.py` for production

### Email Notifications
Set environment variables for email notifications:
```bash
export NOTIFICATION_EMAIL="your-email@gmail.com"
export NOTIFICATION_PASSWORD="your-app-password"
```

### Model Configuration
- YOLOv4 model files stored in `models/` directory
- Confidence threshold: 0.1 - 1.0 (default: 0.5)
- Customize detection classes in `main.py`

## 🛡️ Security Features

### App Protection System
- **File Integrity Monitoring**: SHA256 hashing of critical files
- **Directory Monitoring**: Detects app directory deletion/movement
- **Heartbeat System**: Regular status checks every 5 minutes
- **Emergency Logging**: Backup logging when database is inaccessible
- **Email Alerts**: Immediate notifications to parents on tampering

### Privacy & Data Protection
- **Local Processing**: All image analysis happens locally
- **No Cloud Storage**: Images and videos never leave the device
- **Encrypted Storage**: SQLite databases with integrity checks
- **GDPR Compliant**: No personal data sent to external servers

## 🔒 Security & Privacy

This app is designed for local, on-device monitoring, but it has powerful access that you should understand before using or distributing it.

### What the App Can Access
- **Local Images & Folders**: Any images you select for analysis, including Apple Photos (when you enable that feature). macOS will request appropriate permissions.
- **Screen Content (Self-Monitoring)**: When self/parental monitoring is enabled, the app can capture parts of the screen for analysis, specifically Safari when it is frontmost and on YouTube. macOS will require **Screen Recording** permission.
- **App & File Integrity (Protection)**: The App Protection system monitors certain files and processes on the device to detect tampering or removal.

### What Data Is Stored
- **Detection Results**: Stored in local SQLite databases (`jobs.db`, `monitoring.db`, `protection.db`), including filenames, detection timestamps, and confidence scores.
- **Monitoring Sessions**: Device IDs, parent emails, and high-level monitoring statistics.
- **Protection State**: Whether protection is enabled for a device and any tamper alerts.

All of this data remains **on the local machine**. There is no built-in cloud upload of images or databases.

### Email & Notifications
- Email alerts use credentials provided via environment variables (e.g. `NOTIFICATION_EMAIL`, `NOTIFICATION_PASSWORD`).
- For safety, always use **app-specific passwords** where possible (e.g. Gmail App Passwords) and never commit credentials into source control.

### Recommended Safe Practices
- **Explain Monitoring**: Inform users (especially children) that monitoring is enabled and what it does. Ensure compliance with local laws.
- **Limit Network Exposure**: Run the bundled app (which uses `127.0.0.1`) or otherwise avoid exposing the API server publicly on the network.
- **Protect the Device**: Use OS-level security such as macOS user accounts and FileVault to protect local databases.
- **Review Permissions**: Periodically review macOS Privacy & Security settings (Screen Recording, Files & Folders, Photos) to ensure they match your intent.

## 📊 Database Schema

### Jobs Database (`jobs.db`)
```sql
-- Batch processing jobs
CREATE TABLE batch_jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_images INTEGER,
    processed_images INTEGER DEFAULT 0
);

-- Individual detection results
CREATE TABLE job_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    filename TEXT,
    cigarette_detected BOOLEAN,
    max_confidence REAL,
    detection_details TEXT
);
```

### Monitoring Database (`monitoring.db`)
```sql
-- Monitoring sessions
CREATE TABLE monitoring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    parent_email TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Video detections
CREATE TABLE video_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    app_name TEXT,
    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score REAL,
    screenshot_path TEXT
);
```

### Protection Database (`protection.db`)
```sql
-- App protection status
CREATE TABLE app_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    parent_email TEXT NOT NULL,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    protection_enabled BOOLEAN DEFAULT TRUE
);

-- Deletion/tampering alerts
CREATE TABLE deletion_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type TEXT,
    details TEXT,
    email_sent BOOLEAN DEFAULT FALSE
);
```

## 🔌 API Endpoints

### Detection Endpoints
- `POST /detect/single` - Analyze single image
- `POST /detect/batch` - Batch image analysis
- `POST /detect/apple-photos` - Analyze Apple Photos
- `GET /jobs/{job_id}/status` - Get job status
- `GET /jobs/{job_id}/results` - Get job results

### Parental Control Endpoints
- `POST /parental-control/start-monitoring` - Start video monitoring
- `POST /parental-control/stop-monitoring` - Stop monitoring
- `GET /parental-control/stats` - Get monitoring statistics
- `POST /parental-control/send-test-report` - Send test report
- `GET /parental-control/recent-detections` - Get recent detections

### App Protection Endpoints
- `POST /protection/enable` - Enable app protection
- `POST /protection/disable` - Disable app protection
- `GET /protection/status` - Get protection status

## 🧪 Testing

### Manual Testing
1. Test image detection with sample images
2. Verify parental control email notifications
3. Test app protection by modifying files
4. Check mobile app connectivity to API

### Automated Testing
```bash
# Run detection tests
python -m pytest tests/test_detection.py

# Test API endpoints
python -m pytest tests/test_api.py

# Test app protection
python -m pytest tests/test_protection.py
```

## 🚨 Troubleshooting

### Common Issues

**API Connection Failed**
- Ensure API server is running: `python api_server.py`
- Check firewall settings for port 8000
- Update API_BASE_URL in mobile app to correct IP address

**Model Loading Error**
- Run `python setup_models.py` to download model files
- Check `models/` directory contains `yolov4.weights`, `yolov4.cfg`, `coco.names`
- Verify sufficient disk space (model files ~245MB)

**Email Notifications Not Working**
- Set environment variables for email credentials
- Enable "App Passwords" for Gmail accounts
- Check spam folder for test reports

**Mobile App Not Connecting**
- Update `API_BASE_URL` in `mobile-app/App.js` to your computer's IP
- Ensure mobile device and computer are on same network
- Check API server is accessible: `curl http://YOUR_IP:8000/health`

### Debug Mode
Enable debug logging:
```bash
export DEBUG=1
python api_server.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **YOLOv4**: Object detection model by Alexey Bochkovskiy
- **OpenCV**: Computer vision library
- **FastAPI**: Modern web framework for building APIs
- **React Native**: Cross-platform mobile development
- **Expo**: Platform for universal React applications

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Email: support@cigarette-detection.com
- Documentation: [Wiki](https://github.com/your-repo/wiki)

---

**⚠️ Important Note**: This application is designed for parental control and monitoring purposes. Ensure compliance with local privacy laws and regulations when using monitoring features. Always inform users about data collection and monitoring activities.
