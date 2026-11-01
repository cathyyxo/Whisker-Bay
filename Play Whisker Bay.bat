@echo off
title Whisker Bay
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 play.py
) else (
  python play.py
)
if errorlevel 1 pause
