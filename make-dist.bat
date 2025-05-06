@echo off
echo Building SlowCopy distribution...

REM Clean up any existing distribution folder
if exist slowcopy.dist (
    echo Cleaning existing distribution folder...
    del slowcopy.dist\* /Q
) else (
    mkdir slowcopy.dist
)

REM Build the standalone executable with Nuitka
echo Building executable with Nuitka...
call nuitka --windows-icon-from-ico=appicon.ico --windows-console-mode=disable --standalone --enable-plugin=tk-inter slowcopy.py

REM Copy configuration and resource files
echo Copying configuration and resource files...
robocopy ./ ./slowcopy.dist appicon.png config.json gui.json labels.json mail.json version.txt LICENSE README.md

echo Distribution build complete!
echo Files are available in the slowcopy.dist directory.