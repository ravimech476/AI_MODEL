@echo off
REM ============================================================
REM  Double-click this file to launch the Corn Disease Dashboard
REM  It uses the project's venv automatically.
REM ============================================================
cd /d "%~dp0"
echo Starting Corn Disease Dashboard...
call venv\Scripts\activate.bat
streamlit run app.py
pause
