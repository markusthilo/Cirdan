@echo off
echo Building Cirdan distribution...
if exist cirdan.dist rmdir cirdan.dist /S /Q
if exist download_app.dist rmdir download_app.dist /S /Q
echo Building executable with Nuitka...
call python -m nuitka --msvc=latest --windows-icon-from-ico=appicon.ico --windows-console-mode=disable --standalone --enable-plugin=tk-inter cirdan.py
call python -m nuitka --msvc=latest --standalone download_app.py
rmdir cirdan.build /S /Q
rmdir download_app.build /S /Q
echo Writing Version number to file version.txt
cirdan.dist\cirdan.exe -v > version.txt
set /P Version=<version.txt
mkdir ..\Cirdan_v%Version%
download_app.dist\download_app.exe .\ ..\Cirdan_v%Version%
echo Distribution build complete!
