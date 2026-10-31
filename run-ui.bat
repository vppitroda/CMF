@echo off
rem Launched by start.bat in its own window. Log: out\ui.log
cd /d "%~dp0web"
if not exist "%~dp0out" mkdir "%~dp0out"
call npm start > "%~dp0out\ui.log" 2>&1
