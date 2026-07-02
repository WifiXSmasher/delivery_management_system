@echo off
setlocal EnableDelayedExpansion
title TRANSPORT - Starting...
cd /d "%~dp0"

echo ============================================
echo   TRANSPORT - Delivery Management
echo ============================================
echo.

REM ================================================================
REM  CHECK 1: Are we running from inside a ZIP? (user forgot to extract)
REM  Windows runs bat files from temp paths like C:\Users\...\AppData\Local\Temp\...
REM ================================================================
echo "%~dp0" | findstr /I /C:"\\Temp\\" /C:"\\AppData\\Local\\Temp" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [ERROR] It looks like you are running this from inside a ZIP file.
    echo.
    echo  To fix this:
    echo   1. Right-click the ZIP file and choose "Extract All..."
    echo   2. Open the extracted folder
    echo   3. Double-click start.bat from there
    echo.
    pause
    exit /b 1
)

REM ================================================================
REM  CHECK 2: Do required project files exist?
REM  (catches partial copy / corrupted download)
REM ================================================================
if not exist requirements.txt (
    echo [ERROR] "requirements.txt" is missing from the project folder.
    echo  It seems the project was not copied completely.
    echo  Please re-download or re-copy the entire project folder.
    echo.
    pause
    exit /b 1
)
if not exist manage.py (
    echo [ERROR] "manage.py" is missing from the project folder.
    echo  It seems the project was not copied completely.
    echo  Please re-download or re-copy the entire project folder.
    echo.
    pause
    exit /b 1
)

REM ================================================================
REM  CHECK 3: Is the folder path too long? (Windows 260 char limit)
REM  venv adds ~40 chars (venv\Scripts\python.exe), so warn at 200+
REM ================================================================
set "CURRENT_PATH=%~dp0"
set "PATH_LEN=0"
set "TEMP_STR=!CURRENT_PATH!"
:countloop
if defined TEMP_STR (
    set "TEMP_STR=!TEMP_STR:~1!"
    set /a PATH_LEN+=1
    goto :countloop
)
if !PATH_LEN! GTR 200 (
    echo [WARNING] Your folder path is very long ^(!PATH_LEN! characters^).
    echo  This may cause "path not found" errors on Windows.
    echo.
    echo  Current path: %~dp0
    echo.
    echo  To fix this: Move this folder closer to the root, for example:
    echo   C:\kap_transport\
    echo.
    pause
    exit /b 1
)

REM ================================================================
REM  CHECK 4: Is Python installed and in PATH?
REM ================================================================
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is NOT installed or not in your system PATH.
    echo.
    echo  To fix this:
    echo   1. Download Python from https://www.python.org/downloads/
    echo   2. Run the installer
    echo   3. IMPORTANT: Check the box "Add Python to PATH" at the bottom
    echo   4. After installation, CLOSE this window and double-click start.bat again
    echo.
    pause
    exit /b 1
)

REM ================================================================
REM  CHECK 5: Is it the Windows Store stub? (very common on Win 10/11)
REM  The stub lives in WindowsApps and opens Microsoft Store instead of running.
REM ================================================================
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_PATH=%%i"
    goto :check_stub
)
:check_stub
echo "!PYTHON_PATH!" | findstr /I /C:"WindowsApps" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    REM Verify by actually trying to get the version
    python --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Python found is the Windows Store stub, not real Python.
        echo.
        echo  To fix this:
        echo   1. Open Windows Settings ^> Apps ^> "App execution aliases"
        echo   2. Turn OFF the entries for "python.exe" and "python3.exe"
        echo   3. Download real Python from https://www.python.org/downloads/
        echo   4. Install it with "Add Python to PATH" checked
        echo   5. CLOSE this window and double-click start.bat again
        echo.
        pause
        exit /b 1
    )
)

REM Show which Python is being used
for /f "delims=" %%i in ('python --version 2^>^&1') do echo [OK] Found %%i
for /f "delims=" %%i in ('where python') do echo      Location: %%i
echo.

REM ================================================================
REM  CHECK 6: Can Python actually run? (catches antivirus blocking)
REM ================================================================
python -c "print('ok')" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is installed but cannot run.
    echo  This is often caused by antivirus software blocking python.exe.
    echo.
    echo  To fix this:
    echo   1. Check your antivirus and whitelist/allow python.exe
    echo   2. Or try running this as Administrator: right-click start.bat ^> Run as administrator
    echo.
    pause
    exit /b 1
)

REM ================================================================
REM  All checks passed - start the application
REM ================================================================

REM Backup DB on every start (safe, never deletes old ones)
if exist kap_transport.db (
    if not exist backups mkdir backups
    for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set d=%%c%%b%%a
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set t=%%a%%b
    copy /Y kap_transport.db "backups\autobackup_!d!_!t!.db" >nul 2>&1
    echo [OK] Auto-backup created.
)

REM Create virtualenv if it doesn't exist, or if it came from Linux/macOS
if exist venv (
    if not exist venv\Scripts\python.exe (
        echo [..] Existing environment is not a Windows virtualenv.
        set "OLD_VENV=venv_unix_backup_%RANDOM%"
        move venv "!OLD_VENV!" >nul
        echo [OK] Old environment moved to !OLD_VENV!.
    )
)

if not exist venv (
    echo [..] First-time setup: creating environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo  Try deleting the "venv" folder if it exists, then run start.bat again.
        pause
        exit /b 1
    )
    echo [OK] Environment created.
)

REM Verify venv Python exists before proceeding
if not exist venv\Scripts\python.exe (
    echo [ERROR] Virtual environment is broken - venv\Scripts\python.exe not found.
    echo  Deleting broken environment and retrying...
    rmdir /s /q venv >nul 2>&1
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Could not recreate virtual environment. Please check your Python installation.
        pause
        exit /b 1
    )
    echo [OK] Environment recreated.
)

REM Verify pip exists in venv (some Python installs skip ensurepip)
if not exist venv\Scripts\pip.exe (
    echo [..] pip not found in environment, installing...
    venv\Scripts\python -m ensurepip --upgrade >nul 2>&1
    if not exist venv\Scripts\pip.exe (
        echo [ERROR] Could not install pip in the virtual environment.
        echo  Your Python installation may be incomplete.
        echo  Reinstall Python from https://www.python.org/downloads/
        echo  and make sure to check "Install pip" during setup.
        pause
        exit /b 1
    )
    echo [OK] pip installed.
)

REM Install/update dependencies
echo [..] Checking dependencies...
venv\Scripts\pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)
echo [OK] Dependencies ready.

REM Run migrations (safe - never deletes data)
echo [..] Checking database...
venv\Scripts\python manage.py migrate --run-syncdb >nul 2>&1
echo [OK] Database ready.

REM Open browser after 2 seconds
echo [..] Opening browser...
start /b cmd /c "timeout /t 2 >nul && start http://localhost:8000"

echo.
echo ============================================
echo  App running at: http://localhost:8000
echo  Default login:  admin / admin123
echo  Press Ctrl+C to stop the server.
echo ============================================
echo.

venv\Scripts\python manage.py runserver 8000
