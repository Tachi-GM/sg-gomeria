@echo off
title Sistema de Gestion - Gomeria El Puente
cd /d "%~dp0"

echo ======================================================
echo    Iniciando Sistema de Gestion - Gomeria El Puente
echo ======================================================
echo.

:: 1. Elegir el interprete de Python: primero el entorno virtual (venv o .venv), si no el del sistema
set "PYTHON_CMD="
if exist "venv\Scripts\python.exe" set "PYTHON_CMD=venv\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

:: 2. Verificar que esten instaladas las librerias principales
"%PYTHON_CMD%" -c "import flask, dotenv" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Faltan librerias de Python o no existe el entorno virtual.
    echo.
    echo Abri PowerShell en esta carpeta y ejecuta, en este orden:
    echo     py -V:3.14 -m venv venv
    echo     .\venv\Scripts\Activate.ps1
    echo     pip install -r requirements.txt
    echo Despues volve a abrir este archivo.
    echo.
    pause
    exit /b 1
)

:: 3. Iniciar el servidor en su propia ventana (si falla, ahi se ve el error)
echo Iniciando servidor local...
start "Servidor - Gomeria El Puente" cmd /k "%PYTHON_CMD% app.py"

:: 4. Esperar unos segundos a que arranque y abrir el navegador
echo Esperando que el servidor arranque...
timeout /t 3 /nobreak >nul
echo Abriendo el sistema en tu navegador...
start "" http://127.0.0.1:5000/login

echo.
echo El sistema quedo funcionando en la otra ventana negra, llamada Servidor.
echo NO la cierres mientras uses el programa. Para apagarlo, cerrala.
echo Esta ventana se cierra sola en unos segundos.
timeout /t 8 >nul
