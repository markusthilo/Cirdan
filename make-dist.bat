@echo off
echo Building Cirdan distribution...

REM Clean up any existing distribution folders
if exist cirdan.dist (
    echo Cleaning existing distribution folder cirdan.dist...
    del cirdan.dist\* /Q
)
if exist cirdown.dist (
    echo Cleaning existing distribution folder cirdan.dist...
    del cirdown.dist\* /Q
)

REM Build the standalone executable with Nuitka
echo Building executable with Nuitka...
call python -m nuitka --windows-icon-from-ico=appicon.ico --windows-console-mode=disable --standalone --enable-plugin=tk-inter cirdan.py
call python -m nuitka --standalone cirdown.py

REM Copy configuration and resource files
echo Copying configuration and resource files...
robocopy ./ ./cirdan.dist appicon.png config.json gui.json labels.json mail.json LICENSE README.md

echo Distribution build complete!
echo Files are available in the cirdan.dist directory.