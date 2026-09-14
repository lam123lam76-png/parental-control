"""Cổng kiểm thử MÔ PHỎNG LOCAL cho quy trình cập nhật Agent từ xa.

PROJECT_RULES.md mục 3.4 yêu cầu: trước khi phát lệnh `force-update-all` lên máy
con thật, phải chạy mô phỏng toàn trình trên máy local và chỉ được phát hành khi
bài test PASS 100%. Trước đây repo KHÔNG có bài test này — file này chính là cổng đó.

Bài test kiểm chứng đúng file `Updater.exe` sẽ được phát hành, bằng hai "agent giả"
nhỏ (PyInstaller stub) chạy trong thư mục tạm, nên KHÔNG hề khởi động agent thật,
không đụng tới `C:\\ProgramData\\ParentalControl`, không gửi lệnh nào lên máy con:

  Kịch bản 1 — cập nhật bình thường:
    tiến trình cũ thoát -> Updater thay file -> tiến trình MỚI chạy và sống sót
  Kịch bản 2 — bản mới crash khi khởi động:
    Updater phải tự khôi phục file .bak và chạy lại bản cũ (không mất kết nối máy con)

Cách chạy:  python tools/test_agent_update_gate.py
Trả về mã 0 khi PASS (được phép phát hành), mã 1 khi FAIL (NGHIÊM CẤM phát hành).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "agent" / "dist"
STUB_DIR = REPO_ROOT / "agent" / "tools_gate_stubs"

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

STUB_OLD_SRC = '''
import os, sys, time
from pathlib import Path
d = Path(sys.executable).parent
(d / "started.log").open("a", encoding="utf-8").write(f"old|{os.getpid()}|{time.time():.2f}\\n")
time.sleep(3)
sys.exit(0)
'''

STUB_NEW_SRC = '''
import os, sys, time
from pathlib import Path
d = Path(sys.executable).parent
(d / "started.log").open("a", encoding="utf-8").write(f"new|{os.getpid()}|{time.time():.2f}\\n")
if (d / "crash.flag").exists():
    sys.exit(1)
time.sleep(120)
sys.exit(0)
'''


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_stub(name: str, source: str, workdir: Path) -> Path:
    """Build a tiny onefile stub with PyInstaller (same toolchain as the real agent)."""
    src = workdir / f"{name}.py"
    src.write_text(source, encoding="utf-8")
    log(f"  [build] {name}.exe ...")
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconsole", "--onefile", "--distpath", str(workdir / "dist"),
            "--workpath", str(workdir / "build"), "--specpath", str(workdir),
            "--name", name, str(src),
        ],
        cwd=str(workdir), capture_output=True, text=True,
    )
    exe = workdir / "dist" / f"{name}.exe"
    if result.returncode != 0 or not exe.exists():
        raise RuntimeError(f"PyInstaller thất bại cho {name}:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return exe


def wait_for_log_entry(log_path: Path, kind: str, timeout: float = 25.0):
    """Chờ một dòng '<kind>|<pid>|<ts>' xuất hiện trong started.log."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                parts = line.split("|")
                if len(parts) == 3 and parts[0] == kind:
                    return parts
        time.sleep(0.4)
    return None


def kill_pids(pids) -> None:
    for pid in pids:
        subprocess.run(["taskkill", "/f", "/pid", str(pid)], capture_output=True)


def run_scenario(name: str, staging_crash: bool, updater_exe: Path, stub_old: Path, stub_new: Path, root: Path) -> bool:
    log(f"\n== Kịch bản: {name} ==")
    install = root / f"install_{name}"
    staged = root / f"staged_{name}"
    for d in (install, staged):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    log_path = install / "started.log"
    pids: list[int] = []

    try:
        # "Máy con" hiện tại: bản CŨ đang chạy + Updater.exe THẬT sẽ được dùng để cập nhật
        shutil.copy2(stub_old, install / "ParentalControlAgent.exe")
        shutil.copy2(updater_exe, install / "Updater.exe")
        old_hash = sha256(install / "ParentalControlAgent.exe")

        old_proc = subprocess.Popen(
            [str(install / "ParentalControlAgent.exe")], cwd=str(install),
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            close_fds=True,
        )
        pids.append(old_proc.pid)
        if not wait_for_log_entry(log_path, "old", timeout=30):
            log("  [FAIL] bản cũ không khởi động được (không thấy log 'old')")
            return False
        log(f"  bản cũ đang chạy (pid {old_proc.pid})")

        # Gói cập nhật: bản MỚI (+ cờ crash cho kịch bản rollback)
        shutil.copy2(stub_new, staged / "ParentalControlAgent.exe")
        if staging_crash:
            (staged / "crash.flag").write_text("1", encoding="utf-8")

        log("  chạy Updater.exe (đúng file sẽ phát hành)...")
        result = subprocess.run(
            [str(install / "Updater.exe"), str(old_proc.pid), str(staged), str(install), "ParentalControlAgent.exe"],
            cwd=str(install), capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log(f"  [FAIL] Updater trả mã {result.returncode}: {result.stdout[-500:]} {result.stderr[-500:]}")
            return False

        # Updater phải chờ tiến trình cũ thoát
        if old_proc.poll() is None:
            log("  [FAIL] tiến trình cũ vẫn còn sống sau khi Updater chạy")
            return False

        current_hash = sha256(install / "ParentalControlAgent.exe")
        bak = install / "ParentalControlAgent.exe.bak"

        if staging_crash:
            # Rollback: file phải quay về bản CŨ và một tiến trình CŨ phải chạy lại
            if not bak.exists():
                log("  [FAIL] không có file .bak để rollback")
                return False
            if current_hash != old_hash:
                log("  [FAIL] bản mới crash nhưng file không được khôi phục về bản cũ")
                return False
            entry = wait_for_log_entry(log_path, "old", timeout=25)
            # lần chạy lại này là tiến trình thứ 2 mang marker 'old'
            if not entry:
                log("  [FAIL] không thấy tiến trình cũ được khởi động lại sau rollback")
                return False
            pids.append(int(entry[1]))
            log("  [PASS] đã rollback về bản cũ và chạy lại (máy con không mất kết nối)")
            return True

        # Cập nhật thường: file phải là bản MỚI (khác hash bản cũ) + tiến trình MỚI đang sống
        if current_hash == old_hash:
            log("  [FAIL] file exe không được thay bằng bản mới")
            return False
        if not bak.exists():
            log("  [WARN] không thấy .bak (Updater có thể đã di chuyển file cũ)")
        entry = wait_for_log_entry(log_path, "new", timeout=25)
        if not entry:
            log("  [FAIL] bản mới không khởi động sau khi cập nhật")
            return False
        pids.append(int(entry[1]))
        if not _pid_alive(int(entry[1])):
            log("  [FAIL] bản mới khởi động rồi tắt ngay")
            return False
        log(f"  [PASS] bản mới đã thay thế và đang chạy (pid {entry[1]})")
        return True
    finally:
        kill_pids(pids)


def _pid_alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/fi", f"pid eq {pid}"], capture_output=True, text=True)
    return str(pid) in (out.stdout or "")


def main() -> int:
    updater = DIST_DIR / "Updater.exe"
    log("=== CỔNG KIỂM THỬ MÔ PHỎNG CẬP NHẬT AGENT (local) ===")
    if not updater.exists():
        log(f"[FAIL] Không thấy {updater} — hãy build agent trước (build_and_pack_agent.bat).")
        return 1
    log(f"Updater.exe: {updater} ({updater.stat().st_size:,} bytes, sha256 {sha256(updater)[:16]}…)")

    root = Path(tempfile.mkdtemp(prefix="pc_update_gate_"))
    log(f"Thư mục tạm: {root}")
    try:
        stub_old = build_stub("stub_old", STUB_OLD_SRC, root)
        stub_new = build_stub("stub_new", STUB_NEW_SRC, root)
        ok1 = run_scenario("update_binh_thuong", False, updater, stub_old, stub_new, root)
        ok2 = run_scenario("ban_moi_crash_rollback", True, updater, stub_old, stub_new, root)
    except Exception as e:
        log(f"[FAIL] lỗi khi chạy cổng kiểm thử: {e}")
        return 1
    finally:
        shutil.rmtree(root, ignore_errors=True)

    log("\n=== KẾT QUẢ ===")
    log(f"  cập nhật bình thường : {'PASS' if ok1 else 'FAIL'}")
    log(f"  rollback khi crash   : {'PASS' if ok2 else 'FAIL'}")
    if ok1 and ok2:
        log("=> PASS 100%: được phép phát hành (force-update) lên máy con.")
        return 0
    log("=> FAIL: NGHIÊM CẤM phát hành lên máy con (PROJECT_RULES 3.4).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
