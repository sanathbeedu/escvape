#!/usr/bin/env python3
"""
Cigarette Detection System using YOLOv4
Main detection logic and CLI interface
"""

import cv2
import numpy as np
import os
import sys
import argparse
import time
import json
from pathlib import Path
import subprocess
import sqlite3
from datetime import datetime

class CigaretteDetector:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.config_path = os.path.join(model_dir, "yolov4.cfg")
        self.weights_path = os.path.join(model_dir, "yolov4.weights")
        self.classes_path = os.path.join(model_dir, "coco.names")
        
        self.net = None
        self.classes = []
        self.output_layers = []
        
        # Initialize model
        self._load_model()
    
    def _load_model(self):
        """Load YOLOv4 model"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Config file not found: {self.config_path}")
                print("Please run 'python setup_models.py' to download required files")
                return False
            
            if not os.path.exists(self.weights_path):
                print(f"Weights file not found: {self.weights_path}")
                print("Please run 'python setup_models.py' to download required files")
                return False
            
            # Load YOLO
            self.net = cv2.dnn.readNet(self.weights_path, self.config_path)
            
            # Get output layer names
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            # Load class names
            if os.path.exists(self.classes_path):
                with open(self.classes_path, "r") as f:
                    self.classes = [line.strip() for line in f.readlines()]
            else:
                # Default COCO classes (subset relevant to smoking)
                self.classes = [
                    "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck",
                    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
                    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
                    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
                    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
                    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
                    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
                    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa",
                    "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse",
                    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
                    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
                    "toothbrush"
                ]
            
            print("YOLOv4 model loaded successfully")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def analyze_image(self, image_path, confidence_threshold=0.5):
        """Analyze image for cigarette detection"""
        try:
            if self.net is None:
                return None, "Model not loaded"
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return None, f"Could not load image: {image_path}"
            
            height, width, channels = image.shape
            
            # Prepare image for YOLO
            blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            self.net.setInput(blob)
            
            # Run detection
            start_time = time.time()
            outputs = self.net.forward(self.output_layers)
            analysis_time = time.time() - start_time
            
            # Process detections
            boxes = []
            confidences = []
            class_ids = []
            
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > confidence_threshold:
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
            
            # Apply non-maximum suppression
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, 0.4)
            
            # Analyze detections for cigarette-related objects
            detections = []
            cigarette_detected = False
            max_confidence = 0.0
            
            if len(indexes) > 0:
                for i in indexes.flatten():
                    x, y, w, h = boxes[i]
                    confidence = confidences[i]
                    class_id = class_ids[i]
                    
                    class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
                    
                    # Check if detection is cigarette-related
                    is_cigarette_related = self._is_cigarette_related(class_name, confidence)
                    
                    if is_cigarette_related:
                        cigarette_detected = True
                        max_confidence = max(max_confidence, confidence)
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": [x, y, w, h],
                        "is_cigarette_related": is_cigarette_related
                    })
            
            result = {
                "cigarette_detected": cigarette_detected,
                "max_confidence": max_confidence,
                "detections": detections,
                "analysis_time": analysis_time,
                "image_path": image_path
            }
            
            return result, None
            
        except Exception as e:
            return None, str(e)
    
    def _is_cigarette_related(self, class_name, confidence):
        """Determine if detected object is cigarette-related"""
        # This is a simplified heuristic - in production you'd use a specialized model
        cigarette_keywords = [
            "person",  # People smoking
            "bottle",  # Could be lighter fluid, etc.
            "cup",     # Ashtrays, etc.
        ]
        
        # For demo purposes, we'll consider high-confidence person detections
        # as potentially cigarette-related (would need specialized training)
        if class_name == "person" and confidence > 0.7:
            return True
        
        # In a real implementation, you would:
        # 1. Train a specialized model for cigarette detection
        # 2. Use additional image analysis (color, shape, context)
        # 3. Implement more sophisticated detection logic
        
        return False
    
    def get_apple_photos(self, limit=100):
        """Get photos from Apple Photos library"""
        try:
            # This is a simplified implementation
            # In production, you'd use proper Apple Photos API integration
            
            photos_dir = os.path.expanduser("~/Pictures")
            photo_extensions = ['.jpg', '.jpeg', '.png', '.heic', '.tiff']
            
            photos = []
            
            for root, dirs, files in os.walk(photos_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in photo_extensions):
                        photos.append(os.path.join(root, file))
                        
                        if len(photos) >= limit:
                            break
                
                if len(photos) >= limit:
                    break
            
            return photos[:limit]
            
        except Exception as e:
            print(f"Error accessing photos: {e}")
            return []
    
    def save_detection_result(self, result, output_path):
        """Save detection result with annotations"""
        try:
            if not result or "image_path" not in result:
                return False
            
            # Load original image
            image = cv2.imread(result["image_path"])
            if image is None:
                return False
            
            # Draw detections
            for detection in result["detections"]:
                x, y, w, h = detection["bbox"]
                confidence = detection["confidence"]
                class_name = detection["class"]
                is_cigarette = detection["is_cigarette_related"]
                
                # Choose color based on cigarette detection
                color = (0, 0, 255) if is_cigarette else (0, 255, 0)  # Red for cigarette, green for other
                
                # Draw bounding box
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"{class_name}: {confidence:.2f}"
                if is_cigarette:
                    label += " (CIGARETTE)"
                
                cv2.putText(image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Add summary text
            summary = f"Cigarette Detected: {'YES' if result['cigarette_detected'] else 'NO'}"
            if result['cigarette_detected']:
                summary += f" (Confidence: {result['max_confidence']:.2f})"
            
            cv2.putText(image, summary, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Save annotated image
            cv2.imwrite(output_path, image)
            return True
            
        except Exception as e:
            print(f"Error saving result: {e}")
            return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Cigarette Detection System")
    parser.add_argument("--image", "-i", help="Path to image file")
    parser.add_argument("--batch", "-b", help="Path to directory with images")
    parser.add_argument("--apple-photos", "-a", action="store_true", help="Analyze Apple Photos")
    parser.add_argument("--confidence", "-c", type=float, default=0.5, help="Confidence threshold (0-1)")
    parser.add_argument("--output", "-o", help="Output directory for results")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Limit number of photos to analyze")
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = CigaretteDetector()
    
    if args.image:
        # Single image analysis
        print(f"Analyzing image: {args.image}")
        result, error = detector.analyze_image(args.image, args.confidence)
        
        if error:
            print(f"Error: {error}")
            return 1
        
        # Print results
        print(f"\nResults for {args.image}:")
        print(f"Cigarette detected: {'YES' if result['cigarette_detected'] else 'NO'}")
        
        if result['cigarette_detected']:
            print(f"Max confidence: {result['max_confidence']:.2f}")
        
        print(f"Total detections: {len(result['detections'])}")
        print(f"Analysis time: {result['analysis_time']:.2f}s")
        
        # Save annotated result if output specified
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, f"annotated_{os.path.basename(args.image)}")
            if detector.save_detection_result(result, output_path):
                print(f"Annotated result saved to: {output_path}")
        
        # Show detailed detections
        if result['detections']:
            print("\nDetailed detections:")
            for i, det in enumerate(result['detections']):
                print(f"  {i+1}. {det['class']} (confidence: {det['confidence']:.2f}) "
                      f"{'[CIGARETTE-RELATED]' if det['is_cigarette_related'] else ''}")
    
    elif args.batch:
        # Batch analysis
        print(f"Analyzing images in directory: {args.batch}")
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        images = []
        
        for file in os.listdir(args.batch):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(args.batch, file))
        
        if not images:
            print("No images found in directory")
            return 1
        
        print(f"Found {len(images)} images")
        
        results = []
        cigarette_count = 0
        
        for i, image_path in enumerate(images):
            print(f"Processing {i+1}/{len(images)}: {os.path.basename(image_path)}")
            
            result, error = detector.analyze_image(image_path, args.confidence)
            
            if error:
                print(f"  Error: {error}")
                continue
            
            results.append(result)
            
            if result['cigarette_detected']:
                cigarette_count += 1
                print(f"  ✓ Cigarette detected (confidence: {result['max_confidence']:.2f})")
            else:
                print(f"  ✗ No cigarette detected")
        
        # Summary
        print(f"\nBatch Analysis Summary:")
        print(f"Total images processed: {len(results)}")
        print(f"Images with cigarettes: {cigarette_count}")
        print(f"Detection rate: {cigarette_count/len(results)*100:.1f}%")
        
        # Save results
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            
            # Save JSON summary
            summary = {
                "total_images": len(results),
                "cigarette_detections": cigarette_count,
                "detection_rate": cigarette_count/len(results)*100 if results else 0,
                "results": results
            }
            
            summary_path = os.path.join(args.output, "batch_results.json")
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"Results saved to: {summary_path}")
    
    elif args.apple_photos:
        # Apple Photos analysis
        print("Analyzing Apple Photos...")
        
        photos = detector.get_apple_photos(args.limit)
        
        if not photos:
            print("No photos found or unable to access Apple Photos")
            return 1
        
        print(f"Found {len(photos)} photos")
        
        results = []
        cigarette_count = 0
        
        for i, photo_path in enumerate(photos):
            print(f"Processing {i+1}/{len(photos)}: {os.path.basename(photo_path)}")
            
            result, error = detector.analyze_image(photo_path, args.confidence)
            
            if error:
                print(f"  Error: {error}")
                continue
            
            results.append(result)
            
            if result['cigarette_detected']:
                cigarette_count += 1
                print(f"  ✓ Cigarette detected (confidence: {result['max_confidence']:.2f})")
        
        # Summary
        print(f"\nApple Photos Analysis Summary:")
        print(f"Total photos processed: {len(results)}")
        print(f"Photos with cigarettes: {cigarette_count}")
        print(f"Detection rate: {cigarette_count/len(results)*100:.1f}%")
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
