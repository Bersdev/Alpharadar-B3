@echo off
REM ============================================================
REM  AlphaRadar B3 - inicia backend (FastAPI) e frontend (Next.js)
REM  Basta dar dois cliques neste arquivo no Windows.
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo [ERRO] Python nao encontrado. Instale em https://www.python.org/downloads/ & pause & exit /b 1)
where npm >nul 2>nul || (echo [ERRO] Node.js nao encontrado. Instale em https://nodejs.org/ & pause & exit /b 1)

echo.
echo [1/4] Preparando ambiente Python (backend\.venv)...
if not exist "backend\.venv\Scripts\python.exe" (
    python -m venv backend\.venv || (echo [ERRO] Falha ao criar o ambiente virtual. & pause & exit /b 1)
)
"backend\.venv\Scripts\python.exe" -m pip install --quiet --prefer-binary -r backend\requirements.txt || (echo [ERRO] Falha ao instalar dependencias Python. & pause & exit /b 1)

echo [2/4] Instalando dependencias do frontend (somente na primeira vez)...
if not exist "frontend\node_modules" (
    call npm --prefix frontend install || (echo [ERRO] Falha no npm install. & pause & exit /b 1)
)

echo [3/4] Iniciando backend Python em http://localhost:8000 ...
start "AlphaRadar - Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"

echo [4/4] Iniciando frontend em http://localhost:3000 ...
start "AlphaRadar - Frontend (Next.js)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 8 /nobreak >nul
start "" http://localhost:3000
echo.
echo Pronto! Dashboard: http://localhost:3000   Documentacao da API: http://localhost:8000/docs
echo Para encerrar, feche as duas janelas abertas.
endlocal
