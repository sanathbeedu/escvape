# 🚀 Quick Setup Guide

## Prerequisites
- Python 3.8+ installed
- Git installed
- Modern web browser

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/sigdet.git
cd sigdet
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download AI Models
```bash
python setup_models.py
```

### 4. Start the System
```bash
# Start API server
python api_server.py

# Open web interface
open web_frontend.html
```

## Usage Options

### 🌐 Web Interface (Recommended)
- Modern, responsive design
- Works on desktop and mobile
- Full feature access
- PWA installable

### 📱 Mobile App
```bash
cd mobile-app
npm install
npx expo start
```

### 💻 Command Line
```bash
# Analyze single image
python main.py --image photo.jpg

# Batch process folder
python main.py --batch /path/to/photos/

# Scan Apple Photos
python main.py --apple-photos
```

## Features
- ✅ AI cigarette detection
- ✅ Parental control monitoring
- ✅ Real-time video surveillance
- ✅ Cross-platform compatibility
- ✅ App protection system

## Support
- Web interface: `http://localhost:8000/web_frontend.html`
- API docs: `http://localhost:8000/docs`
- Mobile access: `http://YOUR_IP:8000/web_frontend.html`
