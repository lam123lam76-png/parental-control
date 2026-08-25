# Agent Installer — Thiết kế

> Trạng thái: **Đã duyệt** (brainstorming) — 2026-08-25
> Mục tiêu: một exe `AgentInstaller.exe` chạy trên máy đích, tự tải và cài agent
> phiên bản mới nhất từ backend, thay vì đóng gói thủ công gửi sang.

## 1. Tóm tắt hiểu biết (Understanding Summary)

1. Xây **Agent Installer** — exe Python (PyInstaller), chạy trên máy đích,
   nhận URL backend qua tham số `--url`, tải `agent-update.zip` từ
   `/static/updates/` rồi cài agent.
2. Hai luồng:
   - **Cài lần đầu** (`--install`, thủ công + admin): kiểm tra agent đã cài
     chưa → chưa thì tải + giải nén + copy vào ProgramData + tạo task Highest
     + start watchdog.
   - **Update** (`--update`, silent): nếu đã cài → so version → tải + ghi đè
     exe + restart watchdog.
3. **Pairing thủ công**: lần đầu agent mở Pairing UI (installer không tự pairing).
4. Ràng buộc: installer cần admin (ghi ProgramData + tạo task); auto-update
   cần admin — được đảm bảo bằng watchdog task `RunLevel=Highest` (không dùng
   manifest `--uac-admin` trên exe agent để tránh lỗi 740 + UAC prompt).
5. Non-goals: không UI phức tạp, không tự pairing, không GitHub Releases,
   không skip-version phức tạp.

## 2. Quyết định (Decision Log)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Nguồn tải | Backend `/static/updates/` hiện tại | Đã có cơ chế phục vụ |
| Luồng | Silent update + install thủ công admin | Theo yêu cầu |
| Pairing | Thủ công (Pairing UI) | User chọn |
| Cấu trúc | Phương án A — 1 exe tự chứa logic | Gọn, tái sử dụng `autostart.py` |
| Vị trí code | `agent_installer/` riêng ở root | Tránh phình zip update |
| Auto-update admin | Dựa vào watchdog task Highest | Tránh lỗi 740 + UAC |
| URL | `--url` tham số, mặc định nguyentruclam.io.vn | Linh hoạt |
| Exit code | 0/1/2/3/4 (success/lỗi/mạng/sai luồng/không admin) | Cho tự động hóa |
| Cache CDN | Cache-buster `?t=<timestamp>` cho version.json + zip | Cloudflare cache zip cũ nhiều ngày; nếu không sẽ tải nhầm bản cũ |
| `.env` máy mới | Installer tự ghi `ProgramData\ParentalControl\.env` (SERVER_URL/BACKEND_URL/WS_URL từ `--url`, giữ key khác) | `utils/config.py` `_require()` + `sys.exit()` khi thiếu → máy chưa cài agent bao giờ sẽ crash ngay, pairing UI không hiện |
| Backup URL | `--backup-url` ghi thêm `BACKUP_SERVER_URL` vào `.env` (tùy chọn) | Failover: agent poll lệnh từ backup API (Vercel) khi WS chính sập; nếu thiếu biến này fallback câm |

## 3. Cấu trúc file

```
agent_installer/
├── agent_installer.py    ← entry point chính
├── build_installer.bat   ← build exe (PyInstaller --onefile --console)
├── requirements.txt      ← requests
└── DESIGN.md             ← tài liệu này
```

`agent_installer/` **không nằm trong `agent/`** vì `build_and_pack_agent.bat`
đóng gói `agent/*.py` vào zip update — đặt riêng tránh phình bản cài.

## 4. Luồng chính

### `--install` (cần admin)
1. Kiểm tra admin → nếu không: "Cần quyền Administrator" → exit 4.
2. `GET {url}/static/updates/version.json` → lỗi mạng → exit 2.
3. Agent đã cài? CÓ → "Dùng --update" → exit 0. CHƯA → tiếp.
4. Tải `agent-update.zip` → giải nén `%TEMP%\pc_installer\` → verify đủ file.
5. Copy 4 file vào `C:\ProgramData\ParentalControl`.
6. Gọi `install_autostart()` từ `agent/protection/autostart.py`
   (Registry Run + Scheduled Task AtLogOn battery-safe Highest).
7. Start watchdog → exit 0.

### `--update` (cần admin)
1. Agent chưa cài? → "Dùng --install" → exit 3.
2. `GET version.json` → so với version hiện tại.
3. Bằng/mới hơn → "Đã mới nhất" → exit 0. Cũ hơn → tiếp.
4. Ghi `shutdown.flag` → kill agent + watchdog cũ.
5. Tải zip → ghi đè 4 file.
6. Xóa `shutdown.flag` → start watchdog mới → exit 0.

### `--auto`
Tự chọn: chưa cài → install; đã cài → update.

### Exit codes
| Code | Ý nghĩa |
|---|---|
| 0 | Thành công |
| 1 | Lỗi chung (giải nén, copy, task...) |
| 2 | Lỗi mạng / không lấy được version.json |
| 3 | Sai luồng |
| 4 | Không phải admin |

## 5. An toàn & Edge cases
- Không nhúng secret; pairing do agent xử lý sau cài.
- Verify zip đủ file + size > 0 trước khi copy (không copy nửa chừng).
- `shutdown.flag` (đúng secret trong `watchdog.py`) chống watchdog race khi update.
- `--install` từ chối nếu agent đã cài (bắt buộc `--update`).
- Log install tại `%TEMP%\pc_installer\installer.log`, không ghi secret.
- Arg phụ `--target` cho dev-test (cài vào thư mục tạm, không đụng agent thật).

## 6. Build
```bat
python -m PyInstaller --onefile --console --name="AgentInstaller" ^
  --paths "D:\Hoàng\PMQL\parental-control\agent" ^
  --hidden-import="requests" agent_installer.py
copy dist\AgentInstaller.exe C:\Test\AgentInstaller.exe
```
Dùng `--console` (in tiến trình/lỗi) — khác agent chạy ngầm. Import
`install_autostart`/`install_scheduled_task` trực tiếp từ `agent/protection/autostart.py`
qua `--paths`.

## 7. Testing (kế hoạch)
- Dry-run + `--install` trên máy test (hỏi user trước khi chạy thật).
- Re-run `--install` khi đã cài → từ chối.
- `--update` bản cũ hơn / mới nhất.
- Không admin → exit 4. Mạng lỗi → exit 2. Zip thiếu file → dừng.
