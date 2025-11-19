@echo off
echo Building Cirdan distribution...

REM Clean up any existing distribution folders
if exist cirdan.dist (
    echo Cleaning existing distribution folder cirdan.dist...
    del cirdan.dist\* /Q
)
if exist download_app.dist (
    echo Cleaning existing distribution folder cirdan.dist...
    del download_app.dist\* /Q
)

REM Build the standalone executable with Nuitka
echo Building executable with Nuitka...
call python -m nuitka --windows-icon-from-ico=appicon.ico --windows-console-mode=disable --standalone --enable-plugin=tk-inter cirdan.py
call python -m nuitka --standalone download_app.py

echo Distribution build complete!
echo Files are available in the cirdan.dist directory.

echo Writing Version number to file version.txt
cirdan.dist\cirdan.exe -v > version.txt

echo All done.
