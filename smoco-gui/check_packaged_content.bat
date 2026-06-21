@echo off
REM Check packaged content

echo ===================================
echo   Checking Packaged Content
echo ===================================
echo.

cd dist\SmocoDesktop\_internal

echo Checking for local modules in base_library.zip...
python -c "import zipfile; z=zipfile.ZipFile('base_library.zip'); files = [n for n in z.namelist() if 'main' in n.lower() or 'gui' in n.lower() or 'i18n' in n.lower() or 'asr' in n.lower() or 'utils' in n.lower()]; print('Found', len(files), 'local modules'); [print(f) for f in files]"

echo.
echo Checking if bundle.py is included...
python -c "import zipfile; z=zipfile.ZipFile('base_library.zip'); print('bundle.py in zip:', 'bundle.py' in str(z.namelist()))"

echo.
echo Checking for .py files in _internal...
dir /s /b *.py 2>nul | findstr /v ".pyc"

echo.
echo Press any key to exit...
pause >nul