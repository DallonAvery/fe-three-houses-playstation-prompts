@echo off
rem Opens the PlayStation Prompts installer window (PS Prompts Installer.ps1 in this folder).
powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0PS Prompts Installer.ps1"
if errorlevel 1 (
  echo.
  echo The installer could not start. See the README for installing by hand.
  pause
)
