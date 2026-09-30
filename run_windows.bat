@echo off
echo ==========================================
echo  Robot Gripper - Hand Gesture Control
echo ==========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from https://python.org
    pause
    exit /b 1
)

:: Install libraries
echo Installing required libraries...
pip install pyserial customtkinter mediapipe opencv-contrib-python pillow
echo.

:: Run the app
echo Starting Hand Gesture Control...
echo.
cd python
python main.py

pause
