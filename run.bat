@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [BSC-GUI] Creando entorno virtual...
    %PY% -m venv .venv
    if errorlevel 1 goto :error

    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 goto :error
) else (
    call ".venv\Scripts\activate.bat"
)

python app.py
exit /b %ERRORLEVEL%

:error
echo.
echo [BSC-GUI] No se pudo iniciar la aplicacion.
pause
exit /b 1
