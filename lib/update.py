#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import sub

class Update:
	'''Chech and download update if newer version is available'''

	FILENAME = 'version.txt'

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

	def install(self, install_path):
		'''Download new version if available'''
		if not self.version:
			return
		print('DEBUG: here comes the update install method')
