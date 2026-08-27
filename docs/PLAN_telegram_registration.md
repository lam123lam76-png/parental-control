# PLAN — Đăng ký thiết bị qua Telegram (duyệt Yes/No)

> Trạng thái: **Đã duyệt** — chờ AI triển khai, sau đó review.
> Kiến trúc đã chốt: **Backend trung gian** + **gắn device vào Parent duy nhất (TelegramSetting)**.

## Mục tiêu
Thay flow đăng ký hiện tại (form Tkinter → `/api/pair`) bằng: agent sau khi cài **chạy ngầm, không gửi dữ liệu giám sát**, tạo **trình xin đăng ký có nút Yes/No** trên Telegram; **chờ phê duyệt**; **No → tự gỡ cài đặt**, **Yes → hoạt động bình thường**.

## Tiêu chí thành công
1. Cài agent mới (chưa credentials) → chạy ngầm, KHÔNG gửi heartbeat/log/screenshot, không tạo device trong DB.
2. Backend gửi tin Telegram kèm thông tin thiết bị + 3 nút `✅ Đồng ý`, `❌ Từ chối`, `🔄 Gửi lại`.
3. Bấm ❌ → agent tự gỡ (kill process, bỏ autostart, xóa thư mục + credentials), gửi Telegram "đã gỡ cài đặt", kết thúc.
4. Bấm ✅ → backend tạo Device, agent lưu credentials, bắt đầu gửi dữ liệu, gửi Telegram "cài đặt thành công + version".
5. Bấm 🔄 → gửi lại trình.
6. Bị từ chối muốn chạy lại → phải cài lại.

## Khả thi Telegram miễn phí
Telegram Bot API free hỗ trợ `InlineKeyboardMarkup` (nút callback), `callback_query`, `getUpdates` long polling. Webhook cần URL public (agent sau NAT không dùng được) → **getUpdates polling trên backend**.

## Sơ đồ luồng
```
Agent(mới) --POST /api/register-request {hardware_uuid, device_name}--> Backend
Backend: tạo PendingRegistration(pending) + gửi Telegram nút Yes/No + poll getUpdates
Parent bấm: ❌ -> rejected | 🔄 -> gửi lại | ✅ -> tạo Device + approved (edit tin nhắn)
Agent: poll GET /api/register-request/{id}/status mỗi ~5s
  rejected -> Telegram "đã gỡ cài đặt" -> self-uninstall -> exit
  approved -> lưu device_id/secret_token (DPAPI) -> Telegram "cài đặt thành công + version" -> start engines
```

## Backend
### Model mới `PendingRegistration` (models.py)
`id`(GUID pk = registration_id), `hardware_uuid`, `device_name`, `status`(pending|approved|rejected|expired), `device_id`(GUID null), `secret_token`(null), `tg_message_id`(int null), `expires_at`, `created_at`. Bảng mới → create_all tự tạo (không cần ALTER).

### Module `core/telegram_approval.py` (mới)
`_tg_send`, `send_registration_message` (InlineKeyboardMarkup, callback_data `approve/reject/resend:{id}`), `edit_registration_message`, `answer_callback`, background poller daemon `getUpdates` (offset riêng, `allowed_updates=["callback_query"]`, khoá chống trùng).

### Endpoints
- `POST /api/register-request` `{hardware_uuid, device_name}` → tạo pending + gửi Telegram → `{registration_id, status}`. Rate-limit 1 active/hw_uuid; thiếu TelegramSetting → 503.
- `GET /api/register-request/{id}/status` → `{status, device_id?, secret_token?}`.
- `POST /api/register-request/{id}/resend` (tùy chọn).

### Tạo Device khi approve
Resolve parent duy nhất (như `/api/pair`), tạo `Device` + đảm bảo User/UserPermission, set device_id/secret_token.

## Agent
### `telegram_registration.py` (mới)
Gọi register-request, poll status 5s (backoff), trả kết quả. `self_uninstall_and_exit()`.

### main.py `initialize()`
Thay `run_pairing_ui` bằng `run_telegram_registration`; KHÔNG start engines trước approved; approved → `credential_store.save_credentials` + alert thành công; rejected/expired → alert + self-uninstall.

### Tự gỡ cài đặt
Tái dùng `Uninstall_Parental_Control.bat`: kill agent/watchdog/updater, gỡ Run key + HKLM, `schtasks /Delete ParentalControlWatchdogTask`, xóa ProgramData + APPDATA + LOCALAPPDATA + credentials, tự kill.

### Cấu hình
Agent không cần TELEGRAM_* (backend giữ bot); dùng `get_hardware_uuid()` từ `pairing_ui.py`.

## Installer / build
- Không đổi flow cài chính. Bump agent **v0011** (`build_and_pack_agent.bat` + `DEFAULT_AGENT_VERSION`).
- Redeploy backend home + Vercel; cấu hình `TelegramSetting`/env `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` trên cả 2.

## Cấu hình Telegram bot (1 lần, thủ công)
@BotFather → token; lấy chat_id phụ huynh; điền vào backend. Chỉ backend poll getUpdates bằng token này.

## Edge cases
Nhiều thiết bị cùng lúc / parent không bấm (expire 24h) / hw_uuid đã có credentials / backend down (agent retry) / Yes nhưng agent bỏ chờ / getUpdates bị tool khác dùng / thiếu bot token (503).

## Note TEST + Task checklist (từng phần)
Xem chi tiết trong cuộc hội thoại đã duyệt — mỗi phần (3a model, 3b telegram module, 3c endpoints, 3d create device, 4 agent, 5 build/deploy) đều có: test thử gì/cách thử + checklist cho AI triển khai.

## Thứ tự triển khai
1. Backend: model → telegram_approval → endpoints.
2. Agent: telegram_registration → main.py wiring → self-uninstall.
3. Build v0011 + deploy home/Vercel + cấu hình Telegram.
4. E2E test.
