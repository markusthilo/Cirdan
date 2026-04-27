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
			return 'skipped'

	def __init__(self, parent_path, rel_paths, max_size: int = 1073741824):
		'''Generate object to calculate hashes'''
		super().__init__()
		self._parent_path = parent_path
		self._rel_paths = rel_paths
		self._max_size = max_size
		self._hashes = list[str]()

	def run(self):
		'''Calculate hashes'''
		for rel_path in self._rel_paths:
			path = self._parent_path / rel_path
			size = path.stat().st_size
			self._hashes.append(self.md5(path) if size > 0 and size <= self._max_size else 'skipped')

	def get_hashes(self):
		'''Return calculated hashes'''
		return self._hashes
