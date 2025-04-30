#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import search
from pathlib import Path

class Checker:
	'''Check source and destination'''

	def __init__(self, config):
		'''Set up checker'''
		self._config = config

	def trigger_exists(self, root_path):
		'''Check if a trigger file exists'''
		for trigger in self._config.triggers:
			path = root_path / trigger
			if path.is_file():
				return path

	def source(self, root_path):
		'''Check if source directory is okay'''
		if not root_path.is_dir():
			raise NotADirectoryError(root_path)
		if trigger := self.trigger_exists(root_path):
			raise PermissionError(trigger)
		if not search(self._config.dir_regex, root_path.name):
			raise NameError(root_path.name)
		relative_path = Path(root_path.name, root_path.relative_to(root_path))
		for path in root_path.rglob('*'):
			if len(f'{relative_path}') > self._config.max_path_len:
				raise OSError(relative_path)
			for pattern in self._config.blacklist:
				if path.match(pattern):
					raise RuntimeWarning(relative_path)

	def target(self):
		'''Check if target and log directories are reachable'''
		for dir in (self._config.target, self._config.log):
			try:
				Path(dir).iterdir()
			except:
				raise NotADirectoryError(dir)

	def destination(self, src_path):
		'''Make destination subdirectory or check existing for trigger files'''
		dst_path = Path(self._config.target, src_path.name)
		dst_path.mkdir(exist_ok=True)
		if dst_path.is_dir():
			if trigger := self.trigger_exists(dst_path):
				raise PermissionError(trigger)
		Path(self._config.log, src_path.name).mkdir(exist_ok=True)
