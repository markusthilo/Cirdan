@echo off
echo Building SlowCopy distribution...

REM Clean up any existing distribution folders
if exist slowcopy.dist (
    echo Cleaning existing distribution folder slowcopy.dist...
    del slowcopy.dist\* /Q
)
if exist slowdown.dist (
    echo Cleaning existing distribution folder slowdown.dist...
    del slowdown.dist\* /Q
)

REM Build the standalone executable with Nuitka
echo Building executable with Nuitka...
call nuitka --windows-icon-from-ico=appicon.ico --windows-console-mode=disable --standalone --enable-plugin=tk-inter slowcopy.py
call nuitka --standalone slowdown.py

REM Copy configuration and resource files
echo Copying configuration and resource files...
robocopy ./ ./slowcopy.dist appicon.png config.json gui.json labels.json mail.json LICENSE README.md

echo Distribution build complete!
echo Files are available in the slowcopy.dist directory.