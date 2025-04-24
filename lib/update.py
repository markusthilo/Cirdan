#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

class Update:
	'''Chech and download update if newer version is available'''

	FILENAME = 'version.txt'

	@staticmethod
	def _int(string):
		return int(sub(r'[^0-9]', '', string))

	def __init__(self, dist_dir):
		'''Check for newer version'''
		self._dir_path = Path(dist_dir)
		self.version = None
		try:
			new_version = self._dir_path.joinpath(self.FILENAME).read_text(encoding='utf-8')
		except:
			return
		if self._int(new_version) > self._int(__version__):
			self.version = new_version

	def get_path(self, user):
		'''Download new version if available'''
		if self.version:
			return self._dir_path / f"slowcopy-{user.lower().replace(' ', '')}_v{self.version}.zip"
