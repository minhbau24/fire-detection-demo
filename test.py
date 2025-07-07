import cv2
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if cap.isOpened():
    print("Camera is available!")
else:
    print("Camera is busy or unavailable!")
cap.release()