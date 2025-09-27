# 🚀 Quick Setup Guide — Vaping & Smoking Detection System

AI-powered detection of smoking in images and videos, including vaping devices and cigarettes.

## Prerequisites
- Python 3.8+ installed
- Git installed
- Modern web browser

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/escvape.git
cd escvape
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

# Open the web interface in your browser
# Visit: http://localhost:8000/
```

## Usage Options

### 🌐 Web Interface (Recommended)
- Modern, responsive design
- Works on desktop and mobile
- Full feature access: detect smoking (vaping devices and cigarettes) in images and videos
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
- ✅ AI-powered detection of smoking in images and videos, including vaping devices and cigarettes
- ✅ Parental control monitoring
- ✅ Real-time video surveillance
- ✅ Cross-platform compatibility
- ✅ App protection system

## Support
- Web interface: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`
- Mobile access: `http://YOUR_IP:8000/web_frontend.html`
