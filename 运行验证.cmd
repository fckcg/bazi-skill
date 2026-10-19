@echo off
cd /d "%~dp0"
chcp 65001 >nul
python -X utf8 scripts/verify_project.py --report verification-run.json
pause
