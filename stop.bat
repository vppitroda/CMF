@echo off
setlocal
rem Stops the UI (4200) and API (5013) process trees, then the containers. Database data is kept.
cd /d "%~dp0"
for %%P in (4200 5013) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
    echo Stopping process %%I on port %%P
    taskkill /PID %%I /T /F >nul 2>&1
  )
)
rem close the (now idle) launcher windows
taskkill /FI "WINDOWTITLE eq Docsearch API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Docsearch UI*" /T /F >nul 2>&1
echo Stopping database
docker compose stop
echo Stopped. (start.bat brings everything back; data is kept in the docker volume.)
