@echo off
title Sistema de Gestion - Gomeria El Puente
cd /d "%~dp0"

echo ======================================================
echo    Iniciando Sistema de Gestion - Gomeria El Puente
echo ======================================================
echo.

:: 1. Detectar el interprete de Python con las librerias instaladas
set PYTHON_CMD=python

if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
        )
    )
)

:: 2. Abrir el navegador en la pantalla de inicio
echo Abriendo el sistema en tu navegador...
start http://127.0.0.1:5000/login

:: 3. Iniciar el servidor Flask
echo Iniciando servidor local...
echo.
echo Presiona Ctrl+C o cerra esta ventana para detener el sistema.
echo ======================================================
echo.
%PYTHON_CMD% app.py

pause
