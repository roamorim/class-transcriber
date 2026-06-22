@echo off
setlocal enabledelayedexpansion
title Instalando Transcriptor de Clases...

set "INSTALL_DIR=%USERPROFILE%\TranscriptorClases"
set "REPO_ZIP=https://github.com/roamorim/class-transcriber/archive/refs/heads/main.zip"
set "TEMP_ZIP=%TEMP%\transcriptor_clases.zip"
set "TEMP_DIR=%TEMP%\transcriptor_tmp"
set "SHORTCUT=%USERPROFILE%\Desktop\Transcriptor de Clases.bat"

:: Si este instalador se esta ejecutando desde dentro de la carpeta que
:: vamos a borrar y recrear, se borraria a si mismo a la mitad de la
:: ejecucion ("no se puede encontrar el archivo en lotes"). Para evitarlo,
:: nos copiamos a una carpeta temporal y nos relanzamos desde ahi.
echo %~dp0| findstr /i /c:"%INSTALL_DIR%" >nul
if %errorlevel%==0 (
    echo  Reiniciando el instalador de forma segura...
    set "SELF_TEMP=%TEMP%\instalar_transcriptor_clases.bat"
    copy /y "%~f0" "!SELF_TEMP!" >nul
    start "Instalando Transcriptor de Clases..." "!SELF_TEMP!"
    exit /b
)

echo.
echo  ==========================================
echo    Transcriptor de Clases - Instalacion
echo  ==========================================
echo.
echo  Si la aplicacion ya esta abierta, cierra ahora la ventana
echo  negra de "Transcriptor de Clases" antes de continuar.
echo.
pause
echo.

:: Descargar aplicacion
echo  Descargando la aplicacion...
curl -L --silent --show-error -o "%TEMP_ZIP%" "%REPO_ZIP%"
if %errorlevel% neq 0 (
    echo  ERROR: no se pudo descargar.
    echo  Verifica tu conexion a internet e intenta de nuevo.
    pause
    exit /b 1
)

:: Extraer archivos
echo  Extrayendo archivos...
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP_DIR%' -Force"
if %errorlevel% neq 0 (
    echo  ERROR al extraer los archivos.
    pause
    exit /b 1
)
:: Solo actualiza los archivos de la aplicacion: nunca toca data\ (tus
:: transcripciones), .env (tu API Key) ni .venv (dependencias ya instaladas).
robocopy "%TEMP_DIR%\class-transcriber-main" "%INSTALL_DIR%" /e /is /it /purge /xd "%INSTALL_DIR%\data" "%INSTALL_DIR%\.venv" /xf "%INSTALL_DIR%\.env" >nul
rmdir /s /q "%TEMP_DIR%"
del /q "%TEMP_ZIP%"

:: Configurar API Key (solo la primera vez; si ya existe se conserva)
if exist "%INSTALL_DIR%\.env" (
    echo.
    echo  Configuracion existente encontrada, se mantiene tu API Key actual.
) else (
    echo.
    echo  ==========================================
    echo    Configuracion - Google API Key
    echo  ==========================================
    echo.
    echo  Necesitas una API Key de Google gratuita.
    echo  Obtenla en: https://aistudio.google.com/apikey
    echo.
    echo  Copia la clave y pegala aqui con Ctrl+V
    echo.
    set /p APIKEY="  Ingresa tu Google API Key: "
    if "!APIKEY!"=="" (
        echo  No ingresaste una clave.
        echo  Vuelve a ejecutar INSTALAR.bat cuando la tengas.
        pause
        exit /b 1
    )
    (
        echo GOOGLE_API_KEY=!APIKEY!
        echo DATA_DIR=./data
    ) > "%INSTALL_DIR%\.env"
)
cd /d "%INSTALL_DIR%"
if not exist data\uploads mkdir data\uploads
if not exist data\pdfs    mkdir data\pdfs

:: Instalar dependencias
echo.
echo  Instalando dependencias...
echo  (esto puede tardar unos minutos)
echo.
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %errorlevel% neq 0 (
    echo  ERROR al instalar el gestor de paquetes.
    pause
    exit /b 1
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
uv sync --quiet
if %errorlevel% neq 0 (
    echo  ERROR al instalar las dependencias.
    pause
    exit /b 1
)

:: Crear acceso directo en el Escritorio
echo @echo off > "%SHORTCUT%"
echo title Transcriptor de Clases >> "%SHORTCUT%"
echo set "PATH=%USERPROFILE%\.local\bin;%%PATH%%" >> "%SHORTCUT%"
echo cd /d "%INSTALL_DIR%" >> "%SHORTCUT%"
echo echo. >> "%SHORTCUT%"
echo echo  Iniciando... cierra esta ventana para apagar la app. >> "%SHORTCUT%"
echo echo. >> "%SHORTCUT%"
echo start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000" >> "%SHORTCUT%"
echo uv run uvicorn app.main:app --port 8000 --host 127.0.0.1 >> "%SHORTCUT%"

echo.
echo  ==========================================
echo    Instalacion completada!
echo.
echo    Se creo el acceso directo en tu Escritorio:
echo    "Transcriptor de Clases.bat"
echo.
echo    Haz doble clic en ese archivo para usar la app.
echo  ==========================================
echo.
pause
endlocal
