@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
for %%P in ("%USERPROFILE%\anaconda3\python.exe" "%USERPROFILE%\miniconda3\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe") do (
  if not defined PY if exist %%P set "PY=%%~P"
)
if not defined PY for /f "delims=" %%i in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PY set "PY=%%i"
if not defined PY (
  echo No Python 3.10+ found. Install Python from https://www.python.org/downloads/ and run this again. > setup_log.txt
  type setup_log.txt & pause & exit /b 1
)
"%PY%" setup_attest.py > setup_log.txt 2>&1
type setup_log.txt
echo.
echo Finished. The log is in setup_log.txt next to this file.
pause
