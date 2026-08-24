# Hướng Dẫn Kiểm Thử End-to-End với Agent Thực Tế

## Yêu cầu trước khi bắt đầu:
1. Hệ thống đã được chạy bằng `docker compose up -d`
2. Backend API đang hoạt động (health check OK)
3. Có quyền truy cập vào máy mục tiêu để cài đặt agent

## Các bước thực hiện:

### Bước 1: Cấu hình môi trường cho agent
Sửa file `agent/.env` với các thông số sau:
```
BACKEND_URL=http://localhost:8000
API_KEY=732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7
AGENT_PASSWORD=Truc@1905s0825811915
DEVICE_NAME=Test_Device_01
SEND_INTERVAL=5
```

### Bước 2: Cài đặt agent trên máy mục tiêu (Windows)
```powershell
# Tạo môi trường Python
cd C:\path\to\agent
python -m venv venv

# Kích hoạt môi trường
.\venv\Scripts\Activate.ps1

# Cập nhật pip và cài đặt dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Chạy agent (dưới chế độ debug để dễ theo dõi)
python main.py --core-only
```

### Bước 3: Kiểm tra kết quả
1. Trong terminal chạy agent, kiểm tra log có dòng "Device registered successfully" hoặc tương tự
2. Trong backend logs:
   ```bash
   docker compose logs backend | grep -i device
   ```
3. Trong database, kiểm tra xem thiết bị đã được tạo:
   ```bash
   docker compose exec db psql -U pcuser -d parental_control -c "SELECT * FROM devices;"
   ```

### Bước 4: Kiểm tra hoạt động tiếp theo
1. Agent nên gửi heartbeat thường xuyên (mỗi SEND_INTERVAL giây)
2. Các log từ agent sẽ được ghi vào database
3. Hình ảnh chụp màn hình có thể upload lên storage

## Lưu ý quan trọng:
- Agent phải chạy với quyền admin để truy cập thông tin hệ thống
- Hệ thống cần có kết nối mạng tới backend (localhost:8000)
- Nếu gặp lỗi 401, kiểm tra lại API_KEY trong cả backend và agent đều giống nhau