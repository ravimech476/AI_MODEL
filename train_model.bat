@echo off
REM ============================================================
REM  Double-click this file to (re)train the XGBoost model.
REM  Only needed once, or when you get new labeled data.
REM ============================================================
cd /d "%~dp0"
echo Training XGBoost model...
call venv\Scripts\activate.bat
python train_xgboost.py
pause
