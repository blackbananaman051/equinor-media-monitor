@echo off
echo === Equinor Media Monitor — Build ===
echo.

echo Installing / updating dependencies...
pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)

echo.
echo Building .exe (this takes 2-3 minutes)...
pyinstaller equinor_monitor.spec --noconfirm
if errorlevel 1 (
    echo ERROR: Build failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete!
echo  Your app is at: dist\EquinorMediaMonitor.exe
echo  Double-click it to run.
echo ============================================
pause
