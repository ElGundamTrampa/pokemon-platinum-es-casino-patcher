@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python casino_patcher.py
) else (
  py -3 casino_patcher.py
)
if errorlevel 1 pause
