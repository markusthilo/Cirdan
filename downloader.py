#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv, executable, exit
from pathlib import Path
from subprocess import Popen
from classes.robocopy import RoboCopy

if __name__ == '__main__':  # start here when run as application
	src_path = Path(argv[1])
	dst_path = Path(argv[2])
	for line in RoboCopy().mirror_dir(src_path, dst_path):
		print(line)
	try:
		Popen(
			[dst_path / 'cirdan.exe'] if Path(executable).name == Path(__file__)
				else ['python', dst_path / 'cirdan.py'],
			start_new_session=True
		)
	except Exception as ex:
		print(f'{type(ex)}: {ex}')
		input('Press Enter to close terminal window...')