from ultralytics import YOLO
import os

# Load YOLOv8 model (you can change this to yolov5 or others if preferred)
model = YOLO('yolov8n.pt')  # 'n' is nano model for fast inference

def detect_objects(image_path):
    """
    Runs YOLO object detection on the given image.
    Returns list of detected objects with labels and confidence.
    """
    results = model(image_path)
    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = model.names[cls_id]
            detections.append({'label': label, 'confidence': conf})
    return detections
