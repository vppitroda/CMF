@echo off
setlocal
rem Starts everything: Postgres -> ingest (scan/extract/load, idempotent) -> API -> UI -> browser.
rem Override the sample folder with:  set DOCSEARCH_ROOT=E:\other\folder  before running.
cd /d "%~dp0"
if "%DOCSEARCH_ROOT%"=="" set "DOCSEARCH_ROOT=D:\CMF\sample"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" ( echo [x] Python venv missing: %PY% & exit /b 1 )
if not exist "%DOCSEARCH_ROOT%" ( echo [x] Sample folder not found: %DOCSEARCH_ROOT% & exit /b 1 )

echo [1/5] Database
docker compose up -d db pgadmin || ( echo [x] docker compose failed - is Docker Desktop running? & exit /b 1 )
set /a tries=0
:waitdb
set "hs="
for /f "delims=" %%H in ('docker inspect -f "{{.State.Health.Status}}" docsearch-db 2^>nul') do set "hs=%%H"
if "%hs%"=="healthy" goto dbok
set /a tries+=1
if %tries% gtr 60 ( echo [x] Database did not become healthy & exit /b 1 )
ping -n 3 127.0.0.1 >nul
goto waitdb
:dbok

echo [2/5] Ingest (scan, extract, load - unchanged files are skipped)
pushd ingest
for %%C in (scan extract load) do (
  "%PY%" -m docsearch_ingest %%C || ( echo [x] ingest %%C failed & popd & exit /b 1 )
)
popd

echo [3/5] API
if not exist web\node_modules ( echo       npm install & pushd web & call npm install & popd )
start "Docsearch API" /min cmd /c ""%~dp0run-api.bat" < nul"
call :waitport 5013 90 || ( echo [x] API did not start - see the "Docsearch API" window & exit /b 1 )

echo [4/5] UI
start "Docsearch UI" /min cmd /c ""%~dp0run-ui.bat" < nul"
call :waitport 4200 120 || ( echo [x] UI did not start - see the "Docsearch UI" window & exit /b 1 )

echo [5/5] Opening browser
start "" http://localhost:4200
echo.
echo Docsearch is running:  UI http://localhost:4200   API http://localhost:5013/swagger
echo Run stop.bat to shut it down.
exit /b 0

:waitport
rem %1 = port, %2 = max seconds (polls every 2s)
set /a n=0
:wp
netstat -ano | findstr /r /c:":%1 .*LISTENING" >nul && exit /b 0
set /a n+=2
if %n% gtr %2 exit /b 1
ping -n 3 127.0.0.1 >nul
goto wp
