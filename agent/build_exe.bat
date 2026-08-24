@echo off
title Build ParentalControlAgent Executable
echo ============================================================
echo Building Standalone Agent Executable with PyInstaller...
echo ============================================================
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --clean ParentalControlAgent.spec
echo.
echo ============================================================
echo BUILD COMPLETE!
echo Executable generated at: agent\dist\ParentalControlAgent.exe
echo ============================================================
pause
