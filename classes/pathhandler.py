#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import compile as re_compile

class PathHandler:
	'''Methods to check and create paths'''

	def __init__(self, config, labels):
		'''Set up checker'''
		self._config = config
		self._labels = labels
		self._re = re_compile(self._config.dir_regex)

	def is_accessable_dir(self, path):
		'''Check if path is accessable'''
		if not path.is_dir():
			return False
		try:
			path.iterdir()
		except:
			return False
		return True

	def get_too_long_path(self, src_path):
		'''Check if path length is okay'''
		max_len = self._config.max_path_len - len(f'{src_path.name}')
		for abs_path in src_path.rglob('*'):
			rel_path = abs_path.relative_to(src_path)
			if len(f'{rel_path}') > max_len:
				return rel_path

	def get_blacklisted(self, src_path):
		'''Get blacklisted path'''
		for path in src_path.rglob('*'):
			for pattern in self._config.blacklist:
				if path.match(pattern):
					return path

	def search_trigger_file(self, dir_path):
		'''Check if a trigger file exists'''
		for trigger in self._config.triggers:
			path = dir_path / trigger
			if path.exists():
				return path

	def check_source_path(self, src_path):
		'''Check if source path is okay'''
		if not src_path.is_dir():
			raise NotADirectoryError(self._labels.bad_source.replace('#', f'{src_path}'))
		if not self._re.match(src_path.name):
			raise PermissionError(self._labels.bad_source.replace('#', f'{src_path}'))
		if path := self.get_too_long_path(src_path):
			raise PerError(self._labels.path_too_long.replace('#', f'{path}'))
		if path := self.get_blacklisted(src_path):
			raise PermissionError(self._labels.blacklisted_path.replace('#', f'{path}'))
		if path := self.search_trigger_file(src_path):
			raise PermissionError(self._labels.bad_file.replace('#', f'{path}'))

	def mk_destination(self, src_path, settings):
		'''Create destination subdir'''
		dst_path = self._config.target_path.joinpath(self._config.destinations[settings.destination], src_path.name)
		if dst_path.is_dir():
			if path := self.search_trigger_file(dst_path):
				raise OSError(self._labels.destination_blocked_by.replace('#', f'{path}'))
		elif dst_path.exists():
			raise OSError(self._labels.bad_destination.replace('#', f'{dst_path}'))
		else:
			dst_path.mkdir(parents=True, exist_ok=True)
		return dst_path

