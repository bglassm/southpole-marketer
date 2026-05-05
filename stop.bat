@echo off
setlocal EnableExtensions

cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker CLI is not installed. Nothing to stop.
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  where docker-compose >nul 2>&1
  if errorlevel 1 (
    echo Docker Compose is not available.
    exit /b 1
  )
  docker-compose down --volumes --remove-orphans
) else (
  docker compose down --volumes --remove-orphans
)

if errorlevel 1 (
  echo Failed to stop Southpole stack.
  exit /b 1
)

echo Southpole stack stopped successfully.
exit /b 0
