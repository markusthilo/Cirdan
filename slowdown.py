#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv
from pathlib import Path
from shutil import rmtree
from lib.config import Config
from lib.robocopy import RoboCopy

if __name__ == '__main__':  # start here when run as application
	dist_path = Path(argv[1]) / 'slowcopy.dist'
	install_path = Path(argv[2])
	old_path = Path(argv[3])
	config = Config(old_path / 'config.json')
	if install_path.samefile(old_path):
		for path in install_path.iterdir():
			if path.is_dir():
				rmtree(path)
			else:
				path.unlink()
	elif not install_path.exists():
		install_path.mkdir()
	elif any(install_path.iterdir()):
		raise FileExistsError(f'{install_path} is not empty')
	robocopy = RoboCopy()
	for line in robocopy.copy_dir(dist_path, install_path):
		print(line)
	if robocopy.returncode > 5:
		raise ChildProcessError(f'RoboCopy returncode: {robocopy.returncode}')
	config.save(path=install_path / 'config.json')