#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import sub
from sys import argv
from pathlib import Path
from lib.robocopy import Robocopy

class Update:
	'''Chech and download update if newer version is available'''

	FILENAME = 'version.txt'
	#subprocess.Popen(cmds, start_new_session=True)

	@staticmethod
	def _int(string):
		return int(sub(r'[^0-9]', '', string))

	def __init__(self, this_version, dist_path):
		'''Check for newer version'''
		self._dist_path = dist_path
		self.version = None
		try:
			new_version = self._dist_path.joinpath(self.FILENAME).read_text(encoding='utf-8')
		except:
			return
		if self._int(new_version) > self._int(this_version):
			self.version = new_version



if __name__ == '__main__':  # start here when run as application
	dist_path = Path(argv[1])
	install_path = Path(argv[2])
	robocopy = RoboCopy()
	for line in robocopy.copy_dir(dist_path, install_path):
		print(line)
	if robocopy.returncode > 5:
		raise ChildProcessError(f'RoboCopy returncode: {robocopy.returncode}')
