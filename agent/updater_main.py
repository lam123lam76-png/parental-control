import os
import shutil
import subprocess
import sys
import time


def wait_for_pid(pid, timeout=10):
    """Wait for a process to exit."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # os.kill on Windows with signal 0 checks if process exists
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.5)
    return False

def run_update(pid: int, staged_dir: str, dest_dir: str, exe_name: str):
    """Run the update process safely and reliably."""
    print(f"Waiting for process {pid} to exit...")
    if not wait_for_pid(pid):
        print("Timeout waiting for process. Forcing kill.")
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"Failed to kill: {e}")
            
    # Terminate Watchdog to prevent race conditions and file lock conflicts during copy
    try:
        subprocess.run(["taskkill", "/f", "/im", "ParentalControlWatchdog.exe"], capture_output=True)
    except Exception:
        pass

    time.sleep(1.0)
    print("Processes stopped. Starting file replacement...")
    
    # Backup old executable
    exe_path = os.path.join(dest_dir, exe_name)
    backup_path = exe_path + ".bak"
    
    if os.path.exists(exe_path):
        for attempt in range(5):
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(exe_path, backup_path)
                break
            except Exception as e:
                print(f"Backup attempt {attempt + 1} failed: {e}")
                time.sleep(0.5)
            
    # Copy all files from staged to dest
    copy_success = True
    try:
        for item in os.listdir(staged_dir):
            if item.lower() == "updater.exe":
                # Don't overwrite currently executing Updater.exe in memory
                continue
            s = os.path.join(staged_dir, item)
            d = os.path.join(dest_dir, item)
            for attempt in range(5):
                try:
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d, ignore_errors=True)
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                    break
                except Exception as e:
                    print(f"Copy {item} attempt {attempt + 1} failed: {e}")
                    time.sleep(0.5)
    except Exception as e:
        print(f"Copy failed: {e}")
        copy_success = False
        # Restore backup
        if os.path.exists(backup_path):
            try:
                shutil.move(backup_path, exe_path)
            except Exception:
                pass
            
    # Remove temporary shutdown flag
    flag_path = os.path.join(r"C:\ProgramData\ParentalControl", "shutdown.flag")
    if os.path.exists(flag_path):
        try:
            os.remove(flag_path)
        except Exception:
            pass

    # Start the new executables independently (Detached Process)
    print("Starting new executables...")
    # On Windows, DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
    # ensures child processes survive independently after Updater.exe terminates.
    detached_flags = 0
    if os.name == 'nt':
        detached_flags = 0x00000008 | 0x00000200 | 0x08000000

    proc = None
    if os.path.exists(exe_path):
        try:
            proc = subprocess.Popen([exe_path], cwd=dest_dir, creationflags=detached_flags)
            print(f"Spawned {exe_name} successfully (PID: {proc.pid}).")
        except Exception as se:
            print(f"Error launching {exe_path}: {se}")
    else:
        print(f"Error: Main executable not found at {exe_path}!")

    # Verify new process survives initial startup (3s health check)
    if proc is not None:
        time.sleep(3.0)
        poll = proc.poll()
        if poll is not None and poll != 0:
            print(f"[CRITICAL] New binary crashed on startup (exitcode {poll})! Triggering Auto-Rollback...")
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, exe_path)
                    subprocess.Popen([exe_path], cwd=dest_dir, creationflags=detached_flags)
                    print("[ROLLBACK] Successfully restored and launched backup executable.")
                except Exception as rbe:
                    print(f"[ROLLBACK ERROR] Failed to restore backup: {rbe}")

    # Also spawn Watchdog immediately to resume cross-monitoring
    watchdog_path = os.path.join(dest_dir, "ParentalControlWatchdog.exe")
    if os.path.exists(watchdog_path) and exe_name.lower() != "parentalcontrolwatchdog.exe":
        try:
            subprocess.Popen([watchdog_path], cwd=dest_dir, creationflags=detached_flags)
            print("Spawned ParentalControlWatchdog.exe successfully.")
        except Exception as we:
            print(f"Failed to spawn Watchdog: {we}")

    time.sleep(0.5)
    print("Update completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: Updater.exe <pid> <staged_dir> <dest_dir> <exe_name>")
        sys.exit(1)
        
    pid = int(sys.argv[1])
    staged_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    exe_name = sys.argv[4]
    
    run_update(pid, staged_dir, dest_dir, exe_name)
    sys.exit(0)
