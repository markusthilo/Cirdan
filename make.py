#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from shutil import move, rmtree
import PyInstaller.__main__
from classes.path import Path
from cirdan import __version__

if __name__ == "__main__":
	print("Removing existing executables")
	for name in ("cirdan.exe", "installer-win.exe"):
		path = Path(name)
		if path.is_file():
			path.unlink()
	print("Launching PyInstaller")
	PyInstaller.__main__.run(["--noconfirm", "make.spec"])
	move("dist/cirdan.exe", "./")
	move("dist/installer-win.exe", "./")
	print("Cleaning up")
	for name in ("build", "dist", "__pycache__", "classes/__pycache__"):
		path = Path(name)
		if path.is_dir():
			rmtree(path)
	Path("version.txt").write_text(f"{__version__}\n", encoding="utf-8")
	print("Done!")
