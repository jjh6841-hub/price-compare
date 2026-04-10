@echo off
echo.
echo =========================================
echo   EXE Build (PyInstaller onedir)
echo =========================================
echo.

set PYTHON=
for %%p in (python python3) do (
    where %%p 1>NUL 2>&1 && set PYTHON=%%p && goto :found
)
echo [ERROR] Python is not installed.
pause ^& exit /b 1

:found
echo Python: %PYTHON%
echo.

echo [1/4] Installing dependencies...
%PYTHON% -m pip install -r requirements.txt -q --no-warn-script-location
%PYTHON% -m pip install pyinstaller -q --no-warn-script-location

echo [2/4] Cleaning previous build...
if exist build     rmdir /s /q build
if exist dist      rmdir /s /q dist

echo [3/4] Building exe (this may take a while)...
%PYTHON% -m PyInstaller price-compare.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check the error messages above.
    pause ^& exit /b 1
)

echo [4/4] Copying files...
xcopy /y app.py           dist\price-compare\ 1>NUL
xcopy /y requirements.txt dist\price-compare\ 1>NUL

echo.
echo =========================================
echo   Build complete!
echo =========================================
echo.
echo   Output: dist\price-compare\price-compare.exe
echo.
echo   Distribute the entire dist\price-compare\ folder.
echo.
pause
