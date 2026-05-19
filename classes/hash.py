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

	def __init__(self, files, max_size=1073741824, kill=None):
		'''Generate object to calculate hashes'''
		super().__init__()
		self.files = files
		self._max_size = max_size
		self._kill_switch = kill

	def run(self):
		'''Calculate hashes'''
		for fd in self.files:
			if self._kill_switch and self._kill_switch.is_set():
				return
			fd['hash'] = self.md5(fd['path']) if fd['size'] > 0 and fd['size'] <= self._max_size else 'skipped'
