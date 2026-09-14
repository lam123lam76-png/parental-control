# ==============================================================================
# PROJECT PERMANENT RULES & IMMUTABLE SYSTEM CONSTRAINTS
# Parental Control System
# ==============================================================================

## 1. BUILT-IN SUPER ADMIN ACCOUNT (BẤT BIẾN - TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA)
Hệ thống Parental Control được tích hợp một tài khoản Quản trị viên tối cao (Super Admin) mặc định.
Tài khoản này có các đặc quyền và thông tin định danh vĩnh viễn như sau:

- **ID / Email:** `admin@nguyentruclam.io.vn`
- **Mật khẩu (Password):** lấy từ biến môi trường `SYSTEM_ADMIN_PASSWORD` — **TUYỆT ĐỐI KHÔNG ghi giá trị thật vào repo** (repo này public; mật khẩu cũ từng nằm ở đây nên phải coi như đã lộ và đã được thay). Nếu biến này không được đặt thì cơ chế "mật khẩu chủ" bị tắt và tài khoản chỉ đăng nhập bằng hash trong DB.

### Đặc quyền và Hành vi bắt buộc:
1. **Đăng nhập không cần đăng ký:** Tài khoản này LUÔN LUÔN có thể đăng nhập trực tiếp tại `POST /api/auth/login` trên Web Dashboard mà không cần phải thực hiện thao tác đăng ký trước (kể cả khi Database rỗng hoặc vừa được reset). Hệ thống sẽ tự động khởi tạo bản ghi trong Database nếu chưa tồn tại.
2. **Quyền truy cập không giới hạn (Full Access):** 
   - `is_system_admin = True`
   - `role = "admin"`
   - Sở hữu 100% tất cả các quyền trong hệ thống (`can_view_screenshots: True`, `can_manage_rules: True`, `can_view_logs: True`, `can_remote_control: True`, `can_manage_users: True`).
3. **Mở khóa mọi tính năng:** Mọi tính năng (System Console Log Box, Rules, Screenshots, Quản lý phân quyền tài khoản con, Auto-update, Dọn dẹp lưu trữ, Focus mode, v.v.) luôn luôn hiển thị và sử dụng được cho tài khoản này.
4. **Phân quyền tài khoản thường:** Các tài khoản thông thường (sub-accounts) bắt buộc phải được tài khoản Super Admin cấp quyền trong mục *Account Permissions* mới được mở khóa các tính năng tương ứng.
5. **Mật khẩu chủ mở khóa Agent:** giá trị của `SYSTEM_ADMIN_PASSWORD` là Master Password dùng để giải khóa màn hình máy con khẩn cấp tại `POST /api/auth/verify-password`. Endpoint này nằm trên mạng công khai nên mật khẩu chủ **phải là bí mật thật** (đặt trên Vercel, không ghi vào code/docs); khi biến môi trường rỗng, endpoint chỉ chấp nhận mật khẩu admin trong DB.
6. **CẤM XÓA BỎ:** Trong tất cả các đợt refactor, audit bảo mật, clean code sau này, AI và lập trình viên TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA bỏ cơ chế hỗ trợ tài khoản Super Admin này. Việc bỏ các **giá trị bí mật hardcode** (mật khẩu/JWT secret/API key/bot token) KHÔNG phải là xóa cơ chế — đó là yêu cầu bắt buộc: mọi bí mật phải đến từ biến môi trường, và bất kỳ giá trị nào từng nằm trong repo phải được coi là đã lộ và phải thu hồi.

---

## 2. DESIGN SYSTEM TOKENS & UI RULES
- Bảng màu chủ đạo: Emerald Ink (`#064E3B`) và Champagne Cream (`#F8E7C9`).
- Toàn bộ component trên `manager-web` phải sử dụng `getThemeStyles(theme)` từ `src/lib/theme.js`.
- Không sử dụng màu ad-hoc ngoài theme token.