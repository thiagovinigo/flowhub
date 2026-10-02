@echo off
setlocal
title Flow Hub
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Node.js nao encontrado. Instale em https://nodejs.org e tente de novo.
  pause
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado. Instale o Python 3.12 e tente de novo.
  pause
  exit /b 1
)
if not exist "flowhub\catalog.db" (
  echo Catalogo nao encontrado. Indexando o acervo...
  python flowhub\indexer.py
)
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:3100"
node server\server.js
pause
