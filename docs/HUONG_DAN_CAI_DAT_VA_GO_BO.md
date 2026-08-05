# HƯỚNG DẪN CÀI ĐẶT, VẬN HÀNH & BẢO TRÌ AGENT (MÁY EM TRAI)

Tài liệu này hướng dẫn chi tiết cách cài đặt phần mềm giám sát lên máy tính của em trai, cách tạm dừng và gỡ bỏ khi cần thiết.

---

## 🛠️ PHẦN 1: CÀI ĐẶT LẦN ĐẦU TẠI MÁY EM TRAI

### Bước 1: Chuẩn bị môi trường
1. Tải và cài đặt **Python 3.10+** (Tích chọn vào ô *"Add Python to PATH"* trong lúc cài).
2. Copy thư mục `agent` (nằm trong `parental-control/agent`) vào một đường dẫn an toàn trên máy em trai (Ví dụ: `C:\ParentalControlAgent`).

### Bước 2: Cài đặt thư viện phụ thuộc
Mở **Command Prompt (cmd)** với quyền Admin tại thư mục `C:\ParentalControlAgent`:
```cmd
cd /d C:\ParentalControlAgent
pip install -r requirements.txt
```

### Bước 3: Cấu hình File `.env`
Mở file `.env` bằng Notepad và đảm bảo các thông tin sau đã chính xác:
```env
SUPABASE_URL=https://whymvwuzjaffltkjkfoj.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
TELEGRAM_BOT_TOKEN=8754890738:AAEGB2dZCXJzlQ-Bzk1zwN3n2HLxAyj8imA
TELEGRAM_CHAT_ID=1326412172
AGENT_PASSWORD=Truc@1905s0825811915
DEVICE_NAME=May_Em_Trai
SEND_INTERVAL=60
```

### Bước 4: Đăng ký Tự Khởi Động Ngầm (Task Scheduler)
- Nhấp chuột phải vào file **`install_task.bat`** → Chọn **"Run as administrator"**.
- Màn hình sẽ hiện thông báo `[OK] Da dang ky thanh cong Task "ParentalControlAgent"!`.
- Từ lúc này, mỗi khi máy tính bật lên và em trai đăng nhập, Agent sẽ tự động chạy ngầm dưới quyền cao nhất mà không xuất hiện bất kỳ cửa sổ nào.

---

## 🛑 PHẦN 2: CÁCH DỪNG PHẦN MỀM TẠM THỜI

Khi bạn muốn tạm tắt Agent để em trai dùng máy tự do:

1. Mở thư mục `C:\ParentalControlAgent`.
2. Click đúp chạy file **`stop_agent.py`**.
3. Chương trình sẽ yêu cầu nhập mật khẩu quản lý:
   - Mật khẩu mặc định: `Truc@1905s0825811915` (hoặc mật khẩu mới nếu bạn đã đổi trên Web App trong tab `⚙️ Cài đặt Mật khẩu`).
4. Nhập đúng mật khẩu → Agent và Watchdog sẽ bị tắt hoàn toàn.

---

## 🗑️ PHẦN 3: CÁCH GỠ BỎ PHẦN MỀM HOÀN TOÀN

Khi không còn nhu cầu quản lý máy tính nữa:

### Bước 1: Hủy tự khởi động ngầm
- Nhấp chuột phải vào file **`uninstall_task.bat`** → Chọn **"Run as administrator"**.
- Màn hình sẽ báo `[OK] Da xoa thanh cong Task!`.

### Bước 2: Dừng các tiến trình đang chạy
- Chạy file **`stop_agent.py`** và nhập mật khẩu để tắt Agent.

### Bước 3: Xóa thư mục
- Xóa toàn bộ thư mục `C:\ParentalControlAgent` khỏi máy tính.
