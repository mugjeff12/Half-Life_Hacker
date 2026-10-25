@echo off
rem Double-click me on Windows to build HalfLifeHacker.exe (needs Python 3.10+ from python.org, "Add to PATH" ticked)
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/ and run this again.
  pause & exit /b 1
)
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
rem add --onefile for a single .exe (slower to start)
python build.py --test %*
echo.
echo Your app is in the "dist" folder.
pause
