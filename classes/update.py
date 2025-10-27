#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import sub
from subprocess import Popen

class Update:
	'''Check for new version and start download if available'''

	def __init__(self, this_version, src_path):
		'''Check for newer version'''
		self._src_path = src_path
		try:
			new_version = self._src_path.joinpath('version.txt').read_text(encoding='utf-8')
		except:
			self.new_version = None
			return
		self.new_version = new_version if self._int(new_version) > self._int(this_version) else None

	def _int(self, string):
		return int(sub(r'[^0-9]', '', string))

	def download(self, install_path):
		'''Launch update downloader'''
		exe_path = self._src_path / 'download_app.dist' / 'download_app.exe'
		cmd = [f'{exe_path}'] if exe_path.is_file() else ['python', self._src_path / 'download_app.py']
		return Popen(
			cmd + [self._src_path, install_path],
			start_new_session=True
		)


