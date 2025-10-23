#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import search
from pathlib import Path

class Checker:
	'''Check source and destination'''

	def __init__(self, config):
		'''Set up checker'''
		for dir_path in (config.target_path, config.log_path):
			try:
				dir_path.iterdir()
			except:
				raise NotADirectoryError(f'{dir_path}')
		self._config = config

	def trigger_exists(self, root_path):
		'''Check if a trigger file exists'''
		for trigger in self._config.triggers:
			path = root_path / trigger
			if path.is_file():
				return path

	def source(self, src_path):
		'''Check if source directory is okay'''
		if not src_path.is_dir():
			raise NotADirectoryError(src_path)
		if trigger := self.trigger_exists(src_path):
			raise PermissionError(trigger)
		if not search(self._config.dir_regex, src_path.name):
			raise NameError(src_path.name)
		relative_path = Path(src_path.name, src_path.relative_to(src_path))
		for path in src_path.rglob('*'):
			if len(f'{relative_path}') > self._config.max_path_len:
				raise OSError(relative_path)
			for pattern in self._config.blacklist:
				if path.match(pattern):
					raise RuntimeWarning(relative_path)

	def destination(self, source_path, settings):
		'''Make destination subdirectory or check existing for trigger files'''
		dst_path = self._config.target_path.joinpath(self._config.destinations[settings.destination], source_path.name)
		dst_path.mkdir(parents=True, exist_ok=True)
		if trigger := self.trigger_exists(dst_path):
			raise PermissionError(trigger)
		self._config.log_path.joinpath(dst_path.name).mkdir(parents=True, exist_ok=True)
		return dst_path
