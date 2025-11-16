#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from time import strftime

class Logger:
	'''Configure Logging'''

	def __init__(self, config, labels):
		'''Generate object to write log files'''
		self.prefix = strftime('%y%m%d_%H%M%S_')
		self._config = config
		self._labels = labels
		src_path = src_path.resolve()
		remote_log_dir_path = self._config.log_path / src_path.name
		self._handlers = dict()
		self._logger = logging.getLogger()
		self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

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

	def error(self, ex):
		'''Log error'''
		logging.error(f'{type(ex).__name__}: {ex}')

	def add_lastlog(self):
		'''Add lastlog file'''
		lastlog_path = self._config.local_path.joinpath / f'{self.prefix}{self._config.lastlog_name}'
		logging.info(f'{self._labels.user} {self._labels.running} {self._config.title} v{self._config.version}')
