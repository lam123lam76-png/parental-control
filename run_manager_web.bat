@echo off
title Parental Control - Manager Web UI
echo ============================================================
echo Starting Manager Web UI (Vite Dev Server)...
echo ============================================================
cd /d "%~dp0manager-web"
npm run dev
pause
