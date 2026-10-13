@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r config\requirements-tested.txt
if errorlevel 1 goto error
echo Setup complete. Open START_PORTFOLIO.bat to launch the suite.
pause
exit /b 0
:error
echo Setup failed. Read the error above and the setup guide in docs.
pause
exit /b 1
