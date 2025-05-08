#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import sub
from subprocess import Popen

class Update:
	'''Check for new version and start download if available'''

	@staticmethod
	def _int(string):
		return int(sub(r'[^0-9]', '', string))

	def __init__(self, this_version, dist_path):
		'''Check for newer version'''
		self._dist_path = dist_path
		try:
			new_version = self._dist_path.joinpath('slowcopy-dist/version.txt').read_text(encoding='utf-8')
		except:
			self.new_version = None
			return
		self.new_version = new_version if self._int(new_version) > self._int(this_version) else None

	def download(self, install_path, old_path):
		'''Launch update downloader'''
		exe_path = self._dist_path / 'slowdown.exe'
		cmd = [f'{exe_path}'] if exe_path.is_file() else ['python', old_path / 'slowdown.py']
		return Popen(
			cmd + [self._dist_path / 'slowcopy-dist', install_path, old_path],
			start_new_session=True
		)


