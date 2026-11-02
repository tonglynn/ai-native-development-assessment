@echo off
rem Attest: what only a person may do. Not available to Claude via MCP.
rem   admin notes
rem   admin review
rem   admin approve --note at-0003 --by owner:finance-lead --reason "..."
rem   admin retract --note at-0001 --reason "policy changed"
chcp 65001 >nul
set "PYTHONPATH=%~dp0app"
set "ATTEST_HOME=%~dp0memory"
set ATTEST_APPROVERS=owner:finance-lead
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m attest.admin %1 --repo "%~dp0ledgerly-demo" %2 %3 %4 %5 %6 %7 %8 %9
