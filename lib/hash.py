#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from threading import Thread
from hashlib import file_digest

class HashThread(Thread):
	'''Calculate hashes'''

	@staticmethod
	def md5(path):
		'''Calculate md5 hash of file'''
		with path.open('rb') as fh:
			return file_digest(fh, 'md5').hexdigest()

	def __init__(self, file_paths):
		'''Generate object to calculate hashes'''
		super().__init__()
		self.file_paths = file_paths

	def run(self):
		'''Calculate hashes'''
		logging.info(f'Starte Berechnung von {len(self.file_paths)} Hash-Werten')
		self.hashes = [self.md5(path) for path in self.file_paths]
		logging.info('Hash-Wert-Berechnung ist abgeschlossen')

	def get_hashes(self):
		'''Return relative paths and hashes'''
		for path, md5 in zip(self.file_paths, self.hashes):
			yield path, md5
