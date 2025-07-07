# Fire Detection System - Documentation

## Mục tiêu bài toán
Xây dựng hệ thống phát hiện cháy tự động từ camera (webcam hoặc stream IP) sử dụng mô hình YOLO, với giao diện web trực quan, cho phép:
- Liệt kê và chọn nhiều camera vật lý hoặc stream IP.
- Stream video trực tiếp từ camera lên web.
- Phát hiện cháy theo thời gian thực trên từng khung hình.
- Hiển thị kết quả phát hiện cháy trực tiếp trên giao diện.

## Kiến trúc tổng thể
- **Backend:** FastAPI (Python) + OpenCV + YOLO (ultralytics)
- **Frontend:** HTML/JS thuần, giao diện động, không reload trang
- **Luồng hoạt động:**
  1. Backend liệt kê các camera vật lý khả dụng.
  2. Người dùng tick chọn camera muốn stream hoặc nhập URL stream.
  3. Mỗi camera được stream lên web qua endpoint `/video/{id}`.
  4. Backend đọc từng frame, chạy YOLO detect cháy, trả về luồng ảnh JPEG.
  5. Frontend hiển thị nhiều khung hình camera cùng lúc, có thể đóng/mở từng camera.

## API chính
- `GET /list-cameras`: Trả về danh sách camera vật lý khả dụng.
- `GET /video/{source}`: Stream video (có detect cháy) từ camera hoặc URL.
- `GET /`: Trả về giao diện web.

## Cách sử dụng
1. Chạy server: `python run_server.py`
2. Truy cập: [http://localhost:8000](http://localhost:8000)
3. Tick chọn camera hoặc nhập URL, nhấn "Bắt đầu phát hiện" để xem stream và kết quả detect cháy.
4. Có thể mở nhiều camera cùng lúc, đóng/mở từng camera linh hoạt.

## Yêu cầu
- Python 3.8+
- Các thư viện: fastapi, uvicorn, opencv-python, ultralytics, pillow, numpy
- File model YOLO (best.pt) đặt cùng thư mục nếu muốn detect cháy

## Lưu ý kỹ thuật
- Mỗi camera chỉ được mở 1 lần duy nhất (backend quản lý qua dict).
- Khi đóng stream, backend sẽ giải phóng camera và nhả tài nguyên.
- Nếu camera bị chiếm dụng hoặc driver lỗi, cần kiểm tra lại các ứng dụng khác hoặc thử cắm lại camera.
- Không nên tự động reload danh sách camera liên tục khi đang stream.

## Demo giao diện
- Tick chọn nhiều camera, mỗi camera một khung hình riêng.
- Đóng/mở từng camera không ảnh hưởng các camera khác.
- Kết quả detect cháy hiển thị trực tiếp trên video.

---

**Tác giả:**
- Hệ thống phát triển bởi nhóm AI/Computer Vision, sử dụng YOLO và FastAPI.
