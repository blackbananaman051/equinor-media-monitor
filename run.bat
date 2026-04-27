@echo off
cd /d "%~dp0"
taskkill /f /im python.exe /fi "WINDOWTITLE eq EquinorMonitor" >nul 2>&1
start "EquinorMonitor" py app.py
