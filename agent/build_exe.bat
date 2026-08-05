@echo off
title DONG GOI PARENTAL CONTROL AGENT SANG FILE EXE
color 0A

echo ==========================================================
echo DANG DONG GOI PYTHON SANG FILE EXE MA HOA NGUON...
echo ==========================================================

python -m pip install pyinstaller Pillow supabase psutil pypiwin32 opacity

python -m PyInstaller --noconfirm --onedir --windowed --name "ParentalControlAgent" --clean main.py

echo.
echo ==========================================================
echo DONG GOI EXE HOAN TAT!
echo Thu muc xuat file: dist\\ParentalControlAgent\\
echo ==========================================================
pause
