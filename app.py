from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cv2
import time
import os
from model import detect_fire

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
def video_feed(source: str):
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

    import gc
    from starlette.requests import Request
    from fastapi import Request as FastapiRequest

    async def generate():
        retry_count = 0
        max_retries = 10
        request: FastapiRequest = None
        try:
            # Lấy request từ context (FastAPI 0.95+)
            import contextvars
            request = contextvars.copy_context().get('request', None)
        except Exception:
            pass
        
        # Kiểm tra client disconnect trước khi bắt đầu stream
        try:
            if request is not None and await request.is_disconnected():
                print("Client already disconnected before streaming.")
                return
        except Exception:
            pass
            
        try:
            while True:
                # Kiểm tra client disconnect thường xuyên hơn
                try:
                    if request is not None and await request.is_disconnected():
                        print("Client disconnected, stopping stream.")
                        break
                except Exception:
                    # Nếu không check được disconnect, giả sử client vẫn kết nối
                    pass
                    
                ret, frame = cap.read()
                if not ret:
                    retry_count += 1
                    if retry_count > max_retries:
                        print("Camera lost or cannot grab frame, stopping stream.")
                        break
                    time.sleep(0.2)
                    continue
                retry_count = 0
                # Detect fire using YOLO model (if model file exists)
                try:
                    if os.path.exists("best.pt"):
                        frame = detect_fire(frame)
                except Exception as e:
                    print(f"Fire detection error: {e}")
                    # Continue without fire detection
                    pass
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = (b"--frame\r\n"
                             b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
                try:
                    yield frame_data
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError, Exception) as e:
                    # Client đã ngắt kết nối (socket.send() raised exception)
                    print(f"Client disconnected during frame send: {type(e).__name__}: {e}")
                    break
                time.sleep(1)  # 15 FPS
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            # Đảm bảo giải phóng camera và xóa khỏi dict
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

from fastapi import Response
@app.post("/stop-stream/{source}")
def stop_stream(source: str):
    """
    Stop the video stream for the given source (camera index or URL).
    """
    global open_cameras
    released = False
    print(f"[debug] Stopping stream for source: {source}")
    # Thử cả dạng str và int làm key
    for key in [source, None]:
        if key is None:
            try:
                key = int(source)
            except Exception:
                print(f"Invalid source format: {source}")
                return Response(content="Invalid source format", status_code=400)
                
        if key in open_cameras:
            cap = open_cameras[key]
            try:
                cap.release()
            except Exception:
                pass
            del open_cameras[key]
            print(f"Stopped stream for source: {key}")
            released = True
    if not released:
        print(f"No active stream found for source: {source}")
    return Response(content="OK", status_code=200)

# Backup GET endpoint if POST doesn't work
@app.get("/stop-stream/{source}")
def stop_stream_get(source: str):
    """
    Stop the video stream for the given source (camera index or URL) - GET fallback.
    """
    return stop_stream(source)
