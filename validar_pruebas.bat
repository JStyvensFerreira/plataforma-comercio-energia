@echo off
REM Validador de las pruebas de los patrones SINGLETON y FACTORY METHOD.
REM Doble clic o: validar_pruebas.bat [singleton^|factory] [-v]

cd /d "%~dp0"
python validar_pruebas.py %*
set CODIGO=%ERRORLEVEL%

echo.
if "%CODIGO%"=="0" (
    echo Todas las pruebas pasaron.
) else (
    echo Hubo pruebas que fallaron. Codigo: %CODIGO%
)
echo.
pause
exit /b %CODIGO%
