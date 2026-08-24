"""
Configure Master Server & Agent to Auto-Start on Windows Boot.
Sets Registry Run keys & Startup shortcuts cleanly.
"""

import os
import sys
import winreg

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_TRAY_APP = os.path.join(PROJECT_ROOT, "server_tray_app.py")

def setup_registry_autostart():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        cmd = f'pythonw.exe "{SERVER_TRAY_APP}"'
        winreg.SetValueEx(key, "ParentalControlMasterServer", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(f"[SUCCESS] Registry AutoStart set: {cmd}")
        return True
    except Exception as e:
        print(f"[ERROR] Registry AutoStart failed: {e}")
        return False

def setup_startup_folder_shortcut():
    try:
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return False
        startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.exists(startup_dir):
            return False

        vbs_path = os.path.join(startup_dir, "Start_ParentalControl_Server.vbs")
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{PROJECT_ROOT}"
WshShell.Run "pythonw.exe """ & "{SERVER_TRAY_APP}" & """", 0, False
'''
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        print(f"[SUCCESS] Startup Folder VBScript created: {vbs_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Startup folder shortcut failed: {e}")
        return False

if __name__ == "__main__":
    print("=== CONFIGURING WINDOWS AUTO-START FOR PARENTAL CONTROL MASTER SERVER ===")
    setup_registry_autostart()
    setup_startup_folder_shortcut()
    print("=== CONFIGURATION COMPLETE ===")
