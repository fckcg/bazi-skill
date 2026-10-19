@echo off
cd /d "%~dp0"
chcp 65001 >nul
python -X utf8 scripts/local_app.py
pause
