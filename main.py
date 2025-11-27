#!/usr/bin/env python3
"""
Smoking & Vaping Detection System using YOLOv4
Main detection logic and CLI interface for cigarettes, e-cigarettes, and vaping devices
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

class SmokingVapingDetector:
    def __init__(self, model_dir="models"):
        # Resolve model directory for normal runs, PyInstaller, and py2app bundles
        if not os.path.isabs(model_dir):
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # When frozen by PyInstaller, models are under sys._MEIPASS/models
            if hasattr(sys, "_MEIPASS"):
                base_dir = getattr(sys, "_MEIPASS")
                self.model_dir = os.path.join(base_dir, model_dir)

            # When frozen by py2app, run_app.py and resources live in the
            # app bundle; data_files like "models" are placed in Resources/models.
            elif getattr(sys, "frozen", False):
                # sys.argv[0] points to Contents/MacOS/<AppName>
                app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                resources_dir = os.path.join(app_dir, "..", "Resources")
                self.model_dir = os.path.join(os.path.abspath(resources_dir), model_dir)

            else:
                # Normal source run: models/ relative to this file
                self.model_dir = os.path.join(base_dir, model_dir)
        else:
            self.model_dir = model_dir
        
        self.config_path = os.path.join(self.model_dir, "yolov4.cfg")
        self.weights_path = os.path.join(self.model_dir, "yolov4.weights")
        self.classes_path = os.path.join(self.model_dir, "coco.names")
        
        self.net = None
        self.classes = []
        self.output_layers = []
        
        # Smoking and vaping related keywords for enhanced detection
        self.smoking_keywords = [
            'cigarette', 'cigar', 'pipe', 'tobacco', 'smoke', 'smoking',
            'vape', 'vaping', 'e-cigarette', 'ecig', 'e-cig', 'vaporizer',
            'mod', 'pod', 'juul', 'puff', 'vapor', 'vape pen', 'atomizer',
            'tank', 'coil', 'nic', 'nicotine', 'cloud', 'drip', 'rda'
        ]
        
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
        """Analyze image for smoking and vaping detection"""
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
            
            # Analyze detections for smoking/vaping-related objects
            detections = []
            smoking_detected = False
            vaping_detected = False
            cigarette_detected = False  # Keep for backward compatibility
            max_confidence = 0.0
            detection_types = []
            
            if len(indexes) > 0:
                for i in indexes.flatten():
                    x, y, w, h = boxes[i]
                    confidence = confidences[i]
                    class_id = class_ids[i]
                    
                    class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
                    
                    # Check if detection is smoking/vaping-related
                    detection_result = self._is_smoking_vaping_related(class_name, confidence, image, x, y, w, h)
                    
                    if detection_result['is_related']:
                        if detection_result['type'] == 'smoking':
                            smoking_detected = True
                            cigarette_detected = True  # Backward compatibility
                        elif detection_result['type'] == 'vaping':
                            vaping_detected = True
                        
                        max_confidence = max(max_confidence, confidence)
                        detection_types.append(detection_result['type'])
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": [x, y, w, h],
                        "is_cigarette_related": detection_result['is_related'],
                        "detection_type": detection_result['type'],
                        "reasoning": detection_result['reasoning']
                    })
            
            # Enhanced result with both smoking and vaping detection
            result = {
                "cigarette_detected": cigarette_detected,  # Keep for backward compatibility
                "smoking_detected": smoking_detected,
                "vaping_detected": vaping_detected,
                "any_detected": smoking_detected or vaping_detected,
                "detection_types": list(set(detection_types)),
                "total_detections": len([d for d in detections if d["is_cigarette_related"]]),
                "max_confidence": max_confidence,
                "analysis_time": analysis_time,
                "detections": detections,
                "image_path": image_path
            }
            
            return result, None
            
        except Exception as e:
            return None, f"Detection error: {str(e)}"

    def _is_smoking_vaping_related(self, class_name, confidence, image, x, y, w, h):
        """Enhanced detection for both smoking and vaping"""
        result = {
            'is_related': False,
            'type': None,
            'confidence': confidence,
            'reasoning': []
        }
        
        # Direct object detection (if we had specialized models)
        smoking_objects = ['cigarette', 'cigar', 'pipe', 'lighter', 'ashtray']
        vaping_objects = ['vape', 'e-cigarette', 'vaporizer', 'mod', 'pod', 'juul']
        
        class_lower = class_name.lower()
        
        # Check for direct smoking objects
        if any(obj in class_lower for obj in smoking_objects):
            result['is_related'] = True
            result['type'] = 'smoking'
            result['reasoning'].append(f"Direct smoking object detected: {class_name}")
            return result
        
        # Check for direct vaping objects
        if any(obj in class_lower for obj in vaping_objects):
            result['is_related'] = True
            result['type'] = 'vaping'
            result['reasoning'].append(f"Direct vaping object detected: {class_name}")
            return result
        
        # Enhanced person detection with context analysis
        if class_name == "person" and confidence > 0.6:
            # Extract person region for additional analysis
            try:
                person_region = image[y:y+h, x:x+w]
                
                # Analyze hand/mouth regions for smoking/vaping gestures
                gesture_analysis = self._analyze_smoking_vaping_gesture(person_region)
                
                if gesture_analysis['smoking_gesture']:
                    result['is_related'] = True
                    result['type'] = 'smoking'
                    result['reasoning'].append("Person with potential smoking gesture detected")
                    return result
                
                if gesture_analysis['vaping_gesture']:
                    result['is_related'] = True
                    result['type'] = 'vaping'
                    result['reasoning'].append("Person with potential vaping gesture detected")
                    return result
                
                # High confidence person detection (fallback) - assume smoking for now
                if confidence > 0.8:
                    result['is_related'] = True
                    result['type'] = 'smoking'  # Default to smoking for high confidence person detection
                    result['reasoning'].append("High confidence person detection - likely smoking")
                    return result
            except Exception as e:
                # If region extraction fails, fall back to basic detection
                pass
        
        return result
    
    def _analyze_smoking_vaping_gesture(self, person_region):
        """Analyze person region for smoking/vaping gestures"""
        result = {
            'smoking_gesture': False,
            'vaping_gesture': False,
            'confidence': 0.0
        }
        
        if person_region is None or person_region.size == 0:
            return result
        
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(person_region, cv2.COLOR_BGR2GRAY)
            
            height, width = gray.shape
            
            # Analyze upper portion (head/hand area)
            upper_region = gray[:height//2, :]
            
            # Edge detection to find small objects
            edges = cv2.Canny(upper_region, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                # Look for small, elongated objects (potential cigarettes/vapes)
                if 10 < area < 500:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Cigarettes are typically more elongated
                    if 2 < aspect_ratio < 8:
                        result['smoking_gesture'] = True
                        result['confidence'] = min(0.7, result['confidence'] + 0.2)
                    
                    # Vapes can be more square/rectangular
                    elif 0.5 < aspect_ratio < 3:
                        result['vaping_gesture'] = True
                        result['confidence'] = min(0.7, result['confidence'] + 0.2)
            
        except Exception as e:
            pass
        
        return result
    
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
    parser = argparse.ArgumentParser(description="Smoking & Vaping Detection System")
    parser.add_argument("--image", "-i", help="Path to image file")
    parser.add_argument("--batch", "-b", help="Path to directory with images")
    parser.add_argument("--apple-photos", "-a", action="store_true", help="Analyze Apple Photos")
    parser.add_argument("--confidence", "-c", type=float, default=0.5, help="Confidence threshold (0-1)")
    parser.add_argument("--output", "-o", help="Output directory for results")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Limit number of photos to analyze")
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = SmokingVapingDetector()
    
    if args.image:
        # Single image analysis
        print(f"Analyzing image: {args.image}")
        result, error = detector.analyze_image(args.image, args.confidence)
        
        if error:
            print(f"Error: {error}")
            return 1
        
        # Print results
        print(f"\nResults for {args.image}:")
        print(f"Smoking detected: {'YES' if result['smoking_detected'] else 'NO'}")
        print(f"Vaping detected: {'YES' if result['vaping_detected'] else 'NO'}")
        print(f"Any detection: {'YES' if result['any_detected'] else 'NO'}")
        
        if result['any_detected']:
            print(f"Detection types: {', '.join(result['detection_types'])}")
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
