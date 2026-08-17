#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
from sys import executable
from subprocess import Popen

class Update:
	'''Check for new version and start download if available'''

	@staticmethod
	def _int(string):
		'''Convert version string into an integer'''
		try:
			version, date = string.split('_')
			return (
				sum(i * p for i, p in zip((int(i) for i in version.split('.', 2)), (10000000000, 100000000, 1000000)))
				+ int(datetime.fromisoformat(date).timestamp() / 86400)
			)
		except:
			return 0

	def __init__(self, this_version, src_path):
		'''Check for newer version'''
		self._src_path = src_path
		try:
			new_version = self._src_path.joinpath('version.txt').read_text(encoding='utf-8').strip()
		except:
			self.new_version = None
			return
		self.new_version = new_version if self._int(new_version) > self._int(this_version) else None

	def download(self, install_path):
		'''Launch update downloader'''
		cmd = ['python', self._src_path / 'downloader.py'] if Path(executable).name.startswith('python') else [self._src_path / 'downloader.exe']
		cmd.append(self._src_path)
		cmd.append(install_path)
		return Popen(cmd, start_new_session=True)


