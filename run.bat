@echo off
REM Finglish Launcher for Windows (DEBUG VERSION)
REM Double-click this file to run the app.
REM
REM This uses the CONSOLE python (python.exe) so you can see errors, tracebacks, and DEBUG messages if the clean icon fails.
REM Hotkey inside app: Strg + D
REM For clean no-console launch, use the Desktop shortcut (uses launch-hidden.vbs + pythonw from .venv).

cd /d "%~dp0"

echo Starting Pinglish (activating .venv)...
echo.

REM Activate the virtual environment explicitly.
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ERROR: .venv not found. Run this from the project folder after creating the venv.
    pause
    exit /b 1
)

REM Now python is the venv's python, which has flet installed.
python main.py

echo.
echo.
echo ================================================
echo Pinglish has exited or failed to start.
echo Look above for Python error traceback.
echo Also check: data\finglish_launch.log
echo ================================================
echo.
pause

