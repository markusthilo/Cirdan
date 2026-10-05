#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from platform import system
from sys import argv, executable
from pathlib import Path
from subprocess import Popen

__system__ = system()

if __system__ == 'Windows':
	from classes.robocopy import RoboCopy
else:
	from classes.rsync import Rsync

if __name__ == '__main__':  # start here when run as application
	src_path = Path(argv[1])
	dst_path = Path(argv[2])
	if __system__ == 'Windows':
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
			input('Press Enter to close installer...')
	else:
		for line in Rsync().mirror_dir(src_path, dst_path):
			print(line)
		try:
			Popen(['python', dst_path / 'cirdan.py'], start_new_session=True)
		except Exception as ex:
			print(f'{type(ex)}: {ex}')
			input('Press Enter to close installer...')