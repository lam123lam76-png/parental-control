import subprocess
import time
import os
import sys

def run_command(cmd, timeout=None):
    print(f"\n[{time.strftime('%H:%M:%S')}] Chạy lệnh: {cmd}")
    try:
        # Use shell=True for simpler docker compose calls
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(f"Lỗi/Cảnh báo: {result.stderr.strip()}")
        return result.returncode
    except subprocess.TimeoutExpired as e:
        print(f"Lệnh đã timeout sau {timeout} giây.")
        if e.stdout:
            print(e.stdout.decode('utf-8', errors='ignore'))
        return 0
    except Exception as e:
        print(f"Lỗi khi chạy lệnh: {e}")
        return 1

def main():
    print("="*50)
    print("BẮT ĐẦU KIỂM THỬ END-TO-END (E2E) PARENTAL CONTROL")
    print("="*50)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Bước 1: Chạy backend
    print("\n--- BƯỚC 1: Khởi động Backend (Docker Compose) ---")
    run_command("docker compose up -d")
    
    print("\nĐang chờ 5 giây để backend khởi động hoàn tất...")
    time.sleep(5)
    
    # Bước 2: Kiểm tra file .env
    print("\n--- BƯỚC 2: Kiểm tra cấu hình Agent ---")
    env_path = os.path.join("agent", ".env")
    if os.path.exists(env_path):
        print(f"OK: Đã tìm thấy {env_path}.")
    else:
        print(f"CẢNH BÁO: Không tìm thấy {env_path}! Bạn cần tạo file này từ agent/.env.example trước khi chạy.")
    
    # Bước 3: Chạy Agent và Kiểm tra Database
    print("\n--- BƯỚC 3: Chạy Agent thử nghiệm (15 giây) ---")
    
    agent_cmd = [sys.executable, os.path.join("agent", "main.py"), "--core-only"]
    print(f"[{time.strftime('%H:%M:%S')}] Khởi chạy Agent: {' '.join(agent_cmd)}")
    
    agent_proc = subprocess.Popen(
        agent_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True,
        cwd=project_root
    )
    
    time.sleep(15)
    
    print("\nĐang dừng Agent...")
    agent_proc.terminate()
    try:
        stdout, stderr = agent_proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        agent_proc.kill()
        stdout, stderr = agent_proc.communicate()
        
    print("\n--- [LOG] Output của Agent ---")
    print(stdout.strip() if stdout else "(Không có output)")
    if stderr:
        print("Lỗi từ Agent:")
        print(stderr.strip())
        
    print("\n--- BƯỚC 4: Kiểm tra log Backend ---")
    run_command("docker compose logs --tail=20 backend")
    
    print("\n--- BƯỚC 5: Kiểm tra Database (bảng devices) ---")
    # Sử dụng -T để không dính lỗi TTY (The input device is not a TTY)
    run_command('docker compose exec -T db psql -U pcuser -d parental_control -c "SELECT * FROM devices;"')
    
    print("\n" + "="*50)
    print("HOÀN TẤT KIỂM THỬ END-TO-END!")
    print("Lưu ý: Nếu vẫn gặp lỗi kết nối hoặc Agent không log được, hãy:")
    print(" 1. Kiểm tra lại firewall port 8000.")
    print(" 2. Kiểm tra log backend chi tiết hơn.")
    print(" 3. Xác minh địa chỉ IP trong agent/.env là chính xác (tránh dùng localhost nếu chạy trên máy ảo).")
    print("="*50)

if __name__ == "__main__":
    main()
