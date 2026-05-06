@echo off
chcp 65001 >nul
title Transcriptor de Clases

if not exist .env (
    echo  No se encontro la configuracion.
    echo  Ejecuta primero INSTALAR.bat
    pause
    exit /b 1
)

echo.
echo  Iniciando Transcriptor de Clases...
echo  Abriendo navegador en unos segundos...
echo.
echo  Para cerrar la aplicacion, cierra esta ventana.
echo.

:: Abrir el navegador despues de 3 segundos
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Iniciar el servidor
uv run uvicorn app.main:app --port 8000 --host 127.0.0.1

echo.
echo  La aplicacion se ha cerrado.
pause
