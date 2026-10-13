@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launcher.py start
) else (
  python launcher.py start
)
if errorlevel 1 pause
