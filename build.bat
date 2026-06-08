@echo off
setlocal enabledelayedexpansion
title Jarvis CRM — Build

echo.
echo ================================================
echo   Jarvis CRM — Generando ejecutable .exe
echo ================================================
echo.

:: ── 1. Verificar dependencias ──────────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no encontrado. Instala Node.js para continuar.
    pause & exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado.
    pause & exit /b 1
)

:: ── 2. Build del frontend React ────────────────────────────────────────
echo [1/4] Construyendo frontend React...
cd ui
call npm install --silent
if %errorlevel% neq 0 (echo [ERROR] npm install fallo & pause & exit /b 1)

call npm run build
if %errorlevel% neq 0 (echo [ERROR] npm run build fallo & pause & exit /b 1)

cd ..
echo       Frontend OK — ui\dist listo.
echo.

:: ── 3. Instalar PyInstaller si no está ────────────────────────────────
echo [2/4] Verificando PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo       Instalando PyInstaller...
    python -m pip install pyinstaller --quiet
)
echo       PyInstaller OK.
echo.

:: ── 4. Instalar dependencias Python ───────────────────────────────────
echo [3/4] Instalando dependencias Python...
python -m pip install -r requirements.txt --quiet
echo       Dependencias OK.
echo.

:: ── 5. Ejecutar PyInstaller ────────────────────────────────────────────
echo [4/4] Empaquetando con PyInstaller...
python -m PyInstaller jarvis.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller fallo. Revisa el log arriba.
    pause & exit /b 1
)

:: ── 6. Copiar archivos necesarios al dist ─────────────────────────────
echo.
echo Copiando archivos de datos...
if not exist "dist\JarvisCRM\data" mkdir "dist\JarvisCRM\data"
if not exist "dist\JarvisCRM\logs" mkdir "dist\JarvisCRM\logs"
if exist ".env" copy ".env" "dist\JarvisCRM\.env" >nul

:: ── 7. Crear acceso directo de lanzamiento ─────────────────────────────
echo.
echo ================================================
echo   BUILD EXITOSO
echo ================================================
echo.
echo   Ejecutable: dist\JarvisCRM\JarvisCRM.exe
echo.
echo   IMPORTANTE — antes de distribuir:
echo   1. Copia tu .env en dist\JarvisCRM\
echo   2. Asegurate de tener Playwright instalado:
echo      python -m playwright install chromium
echo.
echo   Para comprimir todo: zip -r JarvisCRM.zip dist\JarvisCRM\
echo.
pause
