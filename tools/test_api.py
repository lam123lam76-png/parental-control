#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_api.py — Kiểm tra toàn bộ Backend API endpoints
=====================================================
Cách dùng:
    python test_api.py
    python test_api.py --url http://myserver:8000
    python test_api.py --url http://myserver:8000 --key MY_API_KEY

Yêu cầu: pip install requests
"""

import os
import sys
import argparse
import json
import time
import requests
from pathlib import Path

# ── Màu sắc terminal (hoạt động trên Windows 10+) ──
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"
BOLD  = "\033[1m"

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def load_env_key() -> str:
    """Tìm API_KEY từ .env hoặc biến môi trường."""
    # Thử các vị trí .env phổ biến
    for env_path in [".env", "../.env", "backend_api/.env", "../backend_api/.env"]:
        p = Path(env_path)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key and not key.startswith("<"):
                        return key
    return os.getenv("API_KEY", "")


def check(name: str, passed: bool, detail: str = "", warn: bool = False):
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    if passed:
        print(f"  {GREEN}✅ PASS{RESET}: {name}")
        PASS_COUNT += 1
    elif warn:
        print(f"  {YELLOW}⚠️  WARN{RESET}: {name}")
        if detail:
            print(f"         → {detail}")
        WARN_COUNT += 1
    else:
        print(f"  {RED}❌ FAIL{RESET}: {name}")
        if detail:
            print(f"         → {detail}")
        FAIL_COUNT += 1


def section(title: str):
    print(f"\n{CYAN}{BOLD}[{title}]{RESET}")


def test_health(base_url: str):
    section("TEST 1 — Health Check")
    try:
        r = requests.get(f"{base_url}/api/health", timeout=5)
        check("Status code 200", r.status_code == 200,
              f"Nhận được: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            check("Response có trường 'data'", "data" in data)
            check("status = 'ok'",
                  data.get("data", {}).get("status") == "ok",
                  f"Nhận: {data.get('data', {}).get('status')}")
    except requests.exceptions.ConnectionError:
        check("Kết nối được Backend", False,
              f"Không thể kết nối tới {base_url} — Backend có đang chạy không?")
    except Exception as e:
        check("Health check", False, str(e))


def test_auth_no_key(base_url: str):
    section("TEST 2 — Bảo Vệ Không Có API Key")
    try:
        r = requests.get(f"{base_url}/api/devices", timeout=5)
        check("Không có key → 401",
              r.status_code == 401,
              f"Nhận được {r.status_code} — API đang mở công khai!")

        r2 = requests.get(f"{base_url}/api/devices",
                          headers={"Authorization": "Bearer WRONG_KEY_XYZ"}, timeout=5)
        check("Key sai → 401",
              r2.status_code == 401,
              f"Nhận được {r2.status_code}")
    except requests.exceptions.ConnectionError:
        check("Kết nối", False, "Không kết nối được Backend")
    except Exception as e:
        check("Auth protection", False, str(e))


def test_with_key(base_url: str, api_key: str):
    section("TEST 3 — API Với Key Hợp Lệ")
    if not api_key:
        print(f"  {YELLOW}⏭️  Bỏ qua — không tìm thấy API_KEY{RESET}")
        print(f"     Chạy: python test_api.py --key YOUR_API_KEY")
        return

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(f"{base_url}/api/devices", headers=headers, timeout=5)
        check("Lấy danh sách thiết bị → 200",
              r.status_code == 200,
              f"Status: {r.status_code} | {r.text[:100]}")
        if r.status_code == 200:
            data = r.json()
            check("Response có 'devices' key",
                  "devices" in data.get("data", {}),
                  f"Keys nhận được: {list(data.get('data', {}).keys())}")
    except Exception as e:
        check("API with valid key", False, str(e))


def test_verify_password_endpoint(base_url: str):
    section("TEST 4 — Endpoint Xác Thực Mật Khẩu (SEC-03 Fix)")
    try:
        # Test với mật khẩu rõ ràng sai
        r = requests.post(
            f"{base_url}/api/auth/verify-password",
            json={"password": "definitely_wrong_password_xyz_123"},
            timeout=5
        )
        check("Endpoint /api/auth/verify-password tồn tại",
              r.status_code in (200, 401, 400),
              f"Nhận {r.status_code} — endpoint có thể chưa được tạo")
        check("Mật khẩu sai → 401",
              r.status_code == 401,
              f"Nhận {r.status_code} thay vì 401")

        # Test mật khẩu quá ngắn
        r2 = requests.post(
            f"{base_url}/api/auth/verify-password",
            json={"password": "ab"},
            timeout=5
        )
        check("Mật khẩu quá ngắn → 400",
              r2.status_code == 400,
              f"Nhận {r2.status_code} thay vì 400")
    except Exception as e:
        check("verify-password endpoint", False, str(e))


def test_rate_limiting(base_url: str):
    section("TEST 5 — Rate Limiting (Chống Brute Force)")
    try:
        codes = []
        for i in range(20):
            r = requests.get(f"{base_url}/api/health", timeout=3)
            codes.append(r.status_code)

        has_rate_limit = 429 in codes
        check("Có Rate Limiting (429 sau nhiều request nhanh)",
              has_rate_limit,
              "Không có rate limiting — Backend dễ bị tấn công!",
              warn=not has_rate_limit)
    except Exception as e:
        check("Rate limit test", False, str(e))


def test_screenshot_upload_format(base_url: str, api_key: str):
    section("TEST 6 — Định Dạng Upload Ảnh (REL-06)")
    if not api_key:
        print(f"  {YELLOW}⏭️  Bỏ qua — cần API_KEY{RESET}")
        return

    print(f"  ℹ️  Kiểm tra endpoint upload có chấp nhận WebP không...")
    # Tạo file WebP giả nhỏ nhất
    webp_header = (
        b'RIFF\x24\x00\x00\x00WEBPVP8L'
        b'\x18\x00\x00\x00/\x00\x00\x00'
        b'\x10\x07\x10\x11\x11\x88\x88\x08'
        b'\x08\x08\x08\x08\x00'
    )
    from io import BytesIO
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        files = {"file": ("test.webp", BytesIO(webp_header), "image/webp")}
        data  = {"device_id": "00000000-0000-0000-0000-000000000000"}
        r = requests.post(f"{base_url}/api/screenshots/upload",
                          headers={"Authorization": f"Bearer {api_key}"},
                          files=files, data=data, timeout=5)
        # 422 = validation error (device not found) là chấp nhận được - nghĩa là endpoint có
        # 200 = thành công
        # 404 = endpoint không tồn tại → vấn đề
        check("Endpoint upload tồn tại",
              r.status_code != 404,
              f"Status: {r.status_code}")
    except Exception as e:
        check("Screenshot upload test", False, str(e))


def main():
    parser = argparse.ArgumentParser(description="Parental Control API Test Suite")
    parser.add_argument("--url", default=None,
                        help="Backend URL (mặc định: đọc từ .env hoặc http://localhost:8000)")
    parser.add_argument("--key", default=None,
                        help="API Key (mặc định: đọc từ .env)")
    args = parser.parse_args()

    # Tải cấu hình
    api_key = args.key or load_env_key()
    base_url = args.url or "http://localhost:8000"

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  PARENTAL CONTROL — TEST API BACKEND{RESET}")
    print(f"  Địa chỉ: {base_url}")
    print(f"  API Key: {'✅ đã cấu hình' if api_key else '❌ chưa có — một số test bị bỏ qua'}")
    print(f"{BOLD}{'='*55}{RESET}")

    start = time.time()

    test_health(base_url)
    test_auth_no_key(base_url)
    test_with_key(base_url, api_key)
    test_verify_password_endpoint(base_url)
    test_rate_limiting(base_url)
    test_screenshot_upload_format(base_url, api_key)

    elapsed = time.time() - start

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  KẾT QUẢ: {GREEN}{PASS_COUNT} PASS{RESET} | {RED}{FAIL_COUNT} FAIL{RESET} | {YELLOW}{WARN_COUNT} WARN{RESET}")
    print(f"  Thời gian: {elapsed:.1f}s")

    if FAIL_COUNT == 0 and WARN_COUNT == 0:
        print(f"  {GREEN}🎉 Tất cả test đều đạt!{RESET}")
    elif FAIL_COUNT == 0:
        print(f"  {YELLOW}✅ Cơ bản tốt — có {WARN_COUNT} cảnh báo cần xem lại.{RESET}")
    elif FAIL_COUNT <= 2:
        print(f"  {YELLOW}⚠️  Có {FAIL_COUNT} lỗi cần sửa.{RESET}")
    else:
        print(f"  {RED}❌ Nhiều lỗi nghiêm trọng! Hãy kiểm tra Backend.{RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")

    sys.exit(0 if FAIL_COUNT == 0 else 1)


if __name__ == "__main__":
    main()
