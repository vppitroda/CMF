@echo off
rem Launched by start.bat in its own window. Log: out\api.log
cd /d "%~dp0api\Docsearch.Api"
if not exist "%~dp0out" mkdir "%~dp0out"
dotnet run --no-launch-profile --urls http://localhost:5013 > "%~dp0out\api.log" 2>&1
