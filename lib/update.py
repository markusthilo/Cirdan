#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import sub

class Update:
	'''Chech and download update if newer version is available'''

	FILENAME = 'version.txt'

	@staticmethod
	def _int(string):
		return int(sub(r'[^0-9]', '', string))

	def __init__(self, this_version, dir_path):
		'''Check for newer version'''
		self._dir_path = dir_path
		self.version = None
		try:
			new_version = self._dir_path.joinpath(self.FILENAME).read_text(encoding='utf-8')
		except:
			return
		if self._int(new_version) > self._int(this_version):
			self.version = new_version

	def install(self, user):
		'''Download new version if available'''
		if not self.version:
			return
		print('DEBUG: here comes the update install method')
