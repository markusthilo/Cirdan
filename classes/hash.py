#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from threading import Thread
from hashlib import file_digest

class HashThread(Thread):
	'''Calculate hashes'''

	@staticmethod
	def md5(path):
		'''Calculate md5 hash of file'''
		try:
			with path.open('rb') as fh:
				return file_digest(fh, 'md5').hexdigest()
		except:
			return '#####'

	def __init__(self, parent_path, rel_paths):
		'''Generate object to calculate hashes'''
		super().__init__()
		self._parent_path = parent_path
		self._rel_paths = rel_paths

	def run(self):
		'''Calculate hashes'''
		self._hashes = [self.md5(self._parent_path / path) for path in self._rel_paths]

	def get_hashes(self):
		'''Return calculated hashes'''
		return self._hashes
