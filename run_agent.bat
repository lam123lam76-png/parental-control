@echo off
title Parental Control - Silent Desktop Agent
echo Starting Parental Control Agent silently...
cd /d "%~dp0agent"
start "" pythonw main.py
echo Agent started in background.
