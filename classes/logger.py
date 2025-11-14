#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

class Logger:
	'''Configure Logging'''

	def __init__(self):
		'''Generate object to write log files'''
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
		self._handlers = dict()

	def add(self, path, level):
		'''Add log file'''
		self._handlers[path] = logging.FileHandler(mode='w', filename=path)
		self._handlers[path].setFormatter(self._formatter)
		self._handlers[path].setLevel({'debug': logging.DEBUG, 'info': logging.INFO}[level])
		self._logger.addHandler(self._handlers[path])

	def remove(self, path):
		'''Close log file / remove from logging'''
		self._logger.removeHandler(self._handlers.pop(path))

	def move(self, old_path, new_path):
		'''Move log file'''
		self.remove(old_path)
		new_path.write_bytes(old_path.read_bytes())
		old_path.unlink()
