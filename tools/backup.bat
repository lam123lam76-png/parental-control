@echo off
chcp 65001 > nul
echo =======================================================
echo   PARENTAL CONTROL - SAO LUU TU DONG (AUTOMATED BACKUP)
echo =======================================================
echo.

cd /d "%~dp0"
python backup.py

echo.
echo Da hoan tat tien trinh sao luu.
pause