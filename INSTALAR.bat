@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Instalando Transcriptor de Clases...

set "INSTALL_DIR=%USERPROFILE%\TranscriptorClases"
set "REPO_ZIP=https://github.com/roamorim/class-transcriber/archive/refs/heads/main.zip"
set "TEMP_ZIP=%TEMP%\transcriptor_clases.zip"
set "TEMP_DIR=%TEMP%\transcriptor_tmp"
set "SHORTCUT=%USERPROFILE%\Desktop\Transcriptor de Clases.bat"

echo.
echo  ============================================
echo    Transcriptor de Clases -- Instalacion
echo  ============================================
echo.

:: ── Verificar Python ────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python no esta instalado. Abriendo pagina de descarga...
    echo.
    echo  Instala Python y luego vuelve a ejecutar este archivo.
    echo  IMPORTANTE: marca la casilla "Add Python to PATH"
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  %%v encontrado.
echo.

:: ── Descargar aplicacion ────────────────────────────────────────────────────
echo  Descargando la aplicacion...
curl -L --silent --show-error -o "%TEMP_ZIP%" "%REPO_ZIP%"
if %errorlevel% neq 0 (
    echo  ERROR: no se pudo descargar. Verifica tu conexion a internet.
    pause
    exit /b 1
)

:: ── Extraer y copiar archivos (via PowerShell) ───────────────────────────────
echo  Instalando archivos...
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"

powershell -NoProfile -Command ^
    "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP_DIR%' -Force; " ^
    "$src = Get-ChildItem '%TEMP_DIR%' -Directory | Select-Object -First 1 -ExpandProperty FullName; " ^
    "Copy-Item -Path \"$src\*\" -Destination '%INSTALL_DIR%' -Recurse -Force"

if %errorlevel% neq 0 (
    echo  ERROR al extraer los archivos.
    pause
    exit /b 1
)
rmdir /s /q "%TEMP_DIR%"
del /q "%TEMP_ZIP%"

:: ── Configurar API Key ───────────────────────────────────────────────────────
echo.
echo  ============================================
echo    Configuracion -- Google API Key
echo  ============================================
echo.
echo  Necesitas una API Key de Google para la transcripcion.
echo  Puedes obtenerla GRATIS en:
echo.
echo    https://aistudio.google.com/apikey
echo.
echo  (Copia la clave y pegala aqui con Ctrl+V)
echo.
set /p APIKEY="  Ingresa tu Google API Key: "
if "!APIKEY!"=="" (
    echo  No ingresaste una clave. Vuelve a ejecutar INSTALAR.bat cuando la tengas.
    pause
    exit /b 1
)
cd /d "%INSTALL_DIR%"
echo GOOGLE_API_KEY=!APIKEY!> .env
echo DATA_DIR=./data>> .env
if not exist data\uploads mkdir data\uploads
if not exist data\pdfs    mkdir data\pdfs

:: ── Instalar dependencias ────────────────────────────────────────────────────
echo.
echo  Instalando dependencias (puede tardar unos minutos)...
pip install uv --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  ERROR al instalar el gestor de paquetes.
    pause
    exit /b 1
)
uv sync --quiet
if %errorlevel% neq 0 (
    echo  ERROR al instalar las dependencias.
    pause
    exit /b 1
)

:: ── Crear acceso directo en el Escritorio ────────────────────────────────────
echo @echo off                                                          > "%SHORTCUT%"
echo chcp 65001 ^>nul                                                  >> "%SHORTCUT%"
echo title Transcriptor de Clases                                      >> "%SHORTCUT%"
echo cd /d "%INSTALL_DIR%"                                             >> "%SHORTCUT%"
echo echo.                                                             >> "%SHORTCUT%"
echo echo  Iniciando Transcriptor de Clases...                        >> "%SHORTCUT%"
echo echo  Cierra esta ventana para apagar la aplicacion.             >> "%SHORTCUT%"
echo echo.                                                             >> "%SHORTCUT%"
echo start /b cmd /c "timeout /t 3 /nobreak ^>nul ^&^& start http://localhost:8000" >> "%SHORTCUT%"
echo uv run uvicorn app.main:app --port 8000 --host 127.0.0.1        >> "%SHORTCUT%"

echo.
echo  ============================================
echo    Instalacion completada exitosamente!
echo.
echo    Acceso directo creado en el Escritorio:
echo    "Transcriptor de Clases.bat"
echo.
echo    Haz doble clic en ese archivo para usar la app.
echo  ============================================
echo.
pause
endlocal
