@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0control.ps1"
if errorlevel 1 pause
