@echo off
rem Attest: what only a person may do (list notes, retract a note). Not available to Claude via MCP.
rem   admin notes
rem   admin retract --note at-0001 --reason "policy changed"
chcp 65001 >nul
set "PYTHONPATH=%~dp0app"
set "ATTEST_HOME=%~dp0memory"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"C:\Users\23778\AppData\Local\Programs\Python\Python312\python.exe" -m attest.admin %1 --repo "%~dp0ledgerly-demo" %2 %3 %4 %5 %6 %7
