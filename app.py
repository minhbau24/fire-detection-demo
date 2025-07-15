from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cv2
import time
import os
import gc
from fastapi import Request as FastapiRequest, Request
from model import detect_fire
from fastapi import Query

app = FastAPI()

# Cho phép CORS để frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
open_cameras = {}
# Serve static files
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Root endpoint to serve HTML
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>File not found</h1>", status_code=404)

# 1. API liệt kê camera nội bộ với loading optimization
@app.get("/list-cameras")
def list_cameras():
    cameras = []
    max_cameras = 10  # Tăng số camera tối đa để kiểm tra
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        try:
            # Set timeout để tránh blocking lâu
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 giây timeout
            if cap.isOpened():
                # Test read frame để đảm bảo camera hoạt động
                ret, _ = cap.read()
                if ret:
                    # Lấy thông tin camera
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS))
                    cameras.append({
                        "name": f"Camera {i}",
                        "id": str(i),
                        "resolution": f"{width}x{height}",
                        "fps": fps if fps > 0 else "Unknown"
                    })
        except Exception as e:
            print(f"Error checking camera {i}: {e}")
        finally:
            cap.release()
            
    return {"cameras": cameras, "total": len(cameras)}

# 2. Endpoint stream video từ camera được chọn (index hoặc URL)


@app.get("/video/{source}")
def video_feed(source: str, fps: int = Query(5, ge=1, le=30), request: Request = None):
    try:
        source = int(source)  # nếu là số, dùng như webcam index
    except ValueError:
        pass  # nếu không, giữ nguyên URL hoặc đường dẫn stream

    global open_cameras
    cap = open_cameras.get(source)
    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise HTTPException(status_code=404, detail="Cannot open camera/stream")
        open_cameras[source] = cap


    def process_frame(frame):
        """Hàm xử lý frame, ví dụ: detect_fire"""
        try:
            if os.path.exists("best.pt"):
                return detect_fire(frame)
            else:
                return frame
        except Exception as e:
            print(f"Fire detection error: {e}")
            return frame

    from fastapi import Request

    async def generate():
        skip_frame = 0
        SKIP_FRAME_COUNT = 1  # Số frame sẽ bỏ qua giữa các lần detect (ví dụ: detect 1, skip 2)
        try:
            while True:
                # Kiểm tra client disconnect
                if request is not None and await request.is_disconnected():
                    print("Client disconnected, stopping stream.")
                    break
                ret, frame = cap.read()
                if not ret:
                    print("Camera lost or cannot grab frame, stopping stream.")
                    break
                # Skip frame để tăng tốc (chỉ detect mỗi (SKIP_FRAME_COUNT+1) frame)
                if skip_frame == 0:
                    frame_processed = process_frame(frame)
                else:
                    frame_processed = frame
                skip_frame = (skip_frame + 1) % (SKIP_FRAME_COUNT + 1)
                _, buffer = cv2.imencode('.jpg', frame_processed, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                frame_data = (b"--frame\r\n"
                             b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
                try:
                    yield frame_data
                except Exception as e:
                    print(f"Client disconnected during frame send: {type(e).__name__}: {e}")
                    break
                time.sleep(1/max(1, min(fps, 30)))
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            print(f"[cleanup] Releasing camera for source: {source}")
            try:
                cap.release()
            except Exception:
                pass
            if source in open_cameras:
                del open_cameras[source]
                print(f"[cleanup] Removed camera {source} from open_cameras")
            gc.collect()

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
