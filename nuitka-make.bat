python -m nuitka ^
  --onefile ^
  --remove-output ^
  --windows-console-mode=attach ^
  --windows-icon-from-ico=icons\cirdan.ico ^
  --include-data-files=*.json=./ ^
  --include-data-files=icons\cirdan.png=icons\cirdan.png ^
  cirdan.py

python -m nuitka ^
  --onefile ^
  --remove-output ^
  --windows-console-mode=force ^
  --windows-icon-from-ico=icons\downloader.ico ^
  downloader.py
