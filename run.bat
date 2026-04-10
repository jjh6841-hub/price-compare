@echo off
chcp 65001 > nul
echo.
echo =========================================
echo   DB Compare Tool - Streamlit
echo =========================================
echo.

set PYTHON=
for %%p in (python python3) do (
    where %%p >nul 2>&1 && set PYTHON=%%p && goto :found
)
echo [ERROR] Python is not installed.
echo   winget install Python.Python.3.12
pause
exit /b 1

:found
echo Python: %PYTHON%
echo.
echo [1/2] Installing packages...
%PYTHON% -m pip install -r requirements.txt -q --no-warn-script-location

echo [2/2] Starting app...
echo.
echo Press Ctrl+C to stop.
echo.
%PYTHON% -m streamlit run app.py
pause
