@echo off
echo ============================= Running Tests =============================
pytest test/
if %ERRORLEVEL% EQU 0 (
    echo.
    echo BUILD SUCCESS
    echo =============================
) else (
    echo.
    echo BUILD FAILURE
    echo =============================
    exit /b 1
)
