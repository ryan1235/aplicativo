@echo off
setlocal
cd /d "%~dp0"
py build_exe.py --install --clean --zip
pause
