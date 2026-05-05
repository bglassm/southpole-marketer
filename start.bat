@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "DOCKER_DOWNLOAD_URL=https://www.docker.com/products/docker-desktop/"
set "DOCKER_WAIT_SECONDS=240"

call :load_env ".env"
if "%N8N_PORT%"=="" set "N8N_PORT=5678"
if "%PIPELINE_PORT%"=="" set "PIPELINE_PORT=8080"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is required but not installed.
  echo Opening Docker Desktop download page...
  start "" "%DOCKER_DOWNLOAD_URL%"
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  where docker-compose >nul 2>&1
  if errorlevel 1 (
    echo Docker Compose is not available. Please install Docker Desktop.
    start "" "%DOCKER_DOWNLOAD_URL%"
    exit /b 1
  )
  set "COMPOSE_CMD=docker-compose"
) else (
  set "COMPOSE_CMD=docker compose"
)

call :docker_ready
if errorlevel 1 (
  echo Docker is installed but not running. Launching Docker Desktop...
  call :start_docker_desktop
  call :wait_for_docker %DOCKER_WAIT_SECONDS%
  if errorlevel 1 (
    echo Docker daemon did not become ready within %DOCKER_WAIT_SECONDS%s.
    echo Please open Docker Desktop and try again.
    exit /b 1
  )
)

echo Docker is ready. Starting Southpole stack...
call :run_compose up -d --build
if errorlevel 1 (
  echo Failed to start Southpole stack.
  exit /b 1
)

call :wait_http "n8n" "http://localhost:%N8N_PORT%/healthz" 300
if errorlevel 1 exit /b 1

call :wait_http "pipeline" "http://localhost:%PIPELINE_PORT%/health" 180
if errorlevel 1 exit /b 1

echo Opening Southpole Operator UI...
start "" "http://localhost:%PIPELINE_PORT%/ui"
echo Southpole is ready.
exit /b 0

:run_compose
if "%COMPOSE_CMD%"=="docker compose" (
  docker compose %*
) else (
  docker-compose %*
)
exit /b %errorlevel%

:docker_ready
docker info >nul 2>&1
exit /b %errorlevel%

:start_docker_desktop
set "STARTED_DOCKER=0"
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
  start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  set "STARTED_DOCKER=1"
)
if exist "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe" (
  start "" "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"
  set "STARTED_DOCKER=1"
)
if "%STARTED_DOCKER%"=="0" (
  start "" "docker-desktop://dashboard"
)
exit /b 0

:wait_for_docker
set /a ELAPSED=0
set /a LIMIT=%~1
:wait_for_docker_loop
call :docker_ready
if not errorlevel 1 exit /b 0
if !ELAPSED! GEQ !LIMIT! exit /b 1
timeout /t 2 /nobreak >nul
set /a ELAPSED+=2
goto :wait_for_docker_loop

:wait_http
set "SERVICE_NAME=%~1"
set "SERVICE_URL=%~2"
set /a TIMEOUT_SECONDS=%~3
set /a ELAPSED_SECONDS=0
:wait_http_loop
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri '%SERVICE_URL%'; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0
if !ELAPSED_SECONDS! GEQ !TIMEOUT_SECONDS! (
  echo %SERVICE_NAME% was not ready within %TIMEOUT_SECONDS%s.
  exit /b 1
)
timeout /t 2 /nobreak >nul
set /a ELAPSED_SECONDS+=2
goto :wait_http_loop

:load_env
if not exist "%~1" exit /b 0
for /f "usebackq tokens=1,* delims==" %%A in ("%~1") do (
  set "KEY=%%A"
  set "VALUE=%%B"
  if not "!KEY!"=="" if not "!KEY:~0,1!"=="#" set "!KEY!=!VALUE!"
)
exit /b 0
