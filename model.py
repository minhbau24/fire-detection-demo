from ultralytics import YOLO
import cv2
import os

# Load model only if best.pt exists

if os.path.exists("best.pt"):
    try:
        model = YOLO("best.pt") # Load the fine-tuned YOLO model
        print("Fire detection model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None
else:
    print("Warning: best.pt not found. Fire detection will be disabled.")

def detect_fire(frame):
    """
    Detect fire in the given frame using the YOLO model.
    Returns the annotated frame with detection results.
    If model is not available, returns the original frame.
    """
    if model is None:
        return frame
    
    try:
        results = model.predict(source=frame, imgsz=416, conf=0.4)
        annotated_frame = results[0].plot()  # Draw detection results on the frame
        return annotated_frame
    except Exception as e:
        print(f"Error in fire detection: {e}")
        return frame