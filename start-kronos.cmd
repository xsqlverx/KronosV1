@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 scripts\bootstrap_kronos.py %*
    exit /b
)
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.11 scripts\bootstrap_kronos.py %*
    exit /b
)
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>&1
if not errorlevel 1 (
    python scripts\bootstrap_kronos.py %*
    exit /b
)
echo Install Python 3.11 or 3.12, then run start-kronos.cmd again.
exit /b 2
