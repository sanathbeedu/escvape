#!/usr/bin/env python3
"""
Model Setup Script for Cigarette Detection System
Downloads YOLOv4 model files and COCO class names
"""

import os
import urllib.request
import sys
from pathlib import Path

def download_file(url, filename, description=""):
    """Download a file with progress indication"""
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            sys.stdout.write(f"\r{description}: {percent:.1f}% ({downloaded}/{total_size} bytes)")
            sys.stdout.flush()
    
    try:
        print(f"Downloading {description}...")
        urllib.request.urlretrieve(url, filename, progress_hook)
        print(f"\n✓ {description} downloaded successfully")
        return True
    except Exception as e:
        print(f"\n✗ Failed to download {description}: {e}")
        return False

def main():
    """Main setup function"""
    print("Cigarette Detection System - Model Setup")
    print("=" * 50)
    
    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Model files to download
    files_to_download = [
        {
            "url": "https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.cfg",
            "filename": models_dir / "yolov4.cfg",
            "description": "YOLOv4 Configuration"
        },
        {
            "url": "https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights",
            "filename": models_dir / "yolov4.weights",
            "description": "YOLOv4 Weights (245MB)"
        },
        {
            "url": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names",
            "filename": models_dir / "coco.names",
            "description": "COCO Class Names"
        }
    ]
    
    success_count = 0
    
    for file_info in files_to_download:
        # Skip if file already exists
        if file_info["filename"].exists():
            print(f"✓ {file_info['description']} already exists, skipping...")
            success_count += 1
            continue
        
        # Download file
        if download_file(file_info["url"], file_info["filename"], file_info["description"]):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"Setup Complete: {success_count}/{len(files_to_download)} files ready")
    
    if success_count == len(files_to_download):
        print("✅ All model files downloaded successfully!")
        print("\nYou can now run the cigarette detection system:")
        print("  • CLI: python main.py --image path/to/image.jpg")
        print("  • GUI: python desktop_client.py")
        print("  • API: python api_server.py")
    else:
        print("⚠️  Some files failed to download. Please check your internet connection and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
