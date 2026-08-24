import psutil
import time

def kill_agent_and_watchdog():
    target_names = ["ParentalControlAgent.exe", "ParentalControlWatchdog.exe"]
    killed_processes = []
    
    # Iterate and kill
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline'] or []
            
            # Match compiled exe name
            is_target = name in target_names
            
            # Also match python source runs if running from source
            if not is_target and name.lower() == "python.exe":
                cmd_str = " ".join(cmdline).lower()
                if "main.py" in cmd_str or "watchdog.py" in cmd_str:
                    is_target = True
            
            if is_target:
                print(f"[-] Killing process PID {proc.pid}: {name} (Cmd: {' '.join(cmdline)})")
                proc.kill()
                killed_processes.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if killed_processes:
        print(f"[+] Successfully terminated {len(killed_processes)} agent/watchdog processes.")
        print("[!] Testing server detection...")
        print("[*] Please wait ~45 seconds to see if the Telegram channel receives a '⚠️ [MẤT KẾT NỐI] ... mất kết nối đột ngột' alert.")
    else:
        print("[?] No active Parental Control Agent or Watchdog processes found.")

if __name__ == "__main__":
    kill_agent_and_watchdog()
