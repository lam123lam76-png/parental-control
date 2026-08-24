Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Hoàng\PMQL\parental-control"
WshShell.Run "cmd.exe /c ""D:\Hoàng\PMQL\parental-control\run_backend.bat""", 0, False
WshShell.Run "pythonw.exe ""D:\Hoàng\PMQL\parental-control\server_tray_app.py""", 0, False
