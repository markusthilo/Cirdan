#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv
from pathlib import Path
from subprocess import Popen
from classes.robocopy import RoboCopy

if __name__ == '__main__':  # start here when run as application
	src_path = Path(argv[1])
	sub_path = src_path / 'cirdan.dist'
	dst_path = Path(argv[2])
	robocopy = RoboCopy()
	print('Starting download...')
	for line in robocopy.mirror_dir(sub_path, dst_path):	# copy cirdan.dist
		print(line)
	if robocopy.returncode > 5:
		msg = f'RoboCopy reported problems while downloading directory {sub_path}'
		msg += 'Command line: {robocopy}'
		msg += '\nReturncode: {robocopy.returncode}'
		raise ChildProcessError(msg)
	first_robocopy = f'{robocopy}'
	for line in robocopy.copy_files(src_path, dst_path, [	# copy additional files from root dir
		'appicon.png',
		'config.json',
		'gui.json',
		'labels.json',
		'mail.json',
		'LICENSE',
		'README.md'
	]):
		print(line)
	if robocopy.returncode > 5:
		msg = f'RoboCopy reported problems while downloading files from {src_path}'
		msg += 'Command line: {robocopy}'
		msg += '\nReturncode: {robocopy.returncode}'
		raise ChildProcessError(msg)
	print(f'...done executing the following commands:\n{first_robocopy}\n{robocopy}')
	try:
		Popen([dst_path / 'cirdan.exe'], start_new_session=True)
	except Exception as ex:
		print(f'{type(ex)}: {ex}')
		input('Press Enter to close terminal window...')