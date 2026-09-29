#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.regex import RegEx

class Destination:
	'''Destination class'''

	def __init__(self, path, whitelist, blacklist):
		'''Destination settings'''
		super().__init__(path)
		self._path = path
		self.sub_dir_paths = list()
		self._whitelist = RegEx(whitelist) if whitelist else None
		self._blacklist = RegEx(blacklist) if blacklist else None

	def __repr__(self):
		'''Printable destination'''
		return f'{self._path.parent.name}/{self._path.name}'

	def check(self):
		'''Check destination directory'''
		for sub_dir_path in self._path.iterdir():
			if sub_dir_path.is_dir():
				if self._whitelist:
					yield f'{self._path}/{sub_dir_path.name}'
					for path, relative in sub_dir_path.rrglob('*'):
						if self._whitelist.search(relative):
							self.sub_dir_paths.append(sub_dir_path)
						break
				else:
					self.sub_dir_paths.append(sub_dir_path)
		if self._blacklist:
			for sub_dir_path in self.sub_dir_paths.copy():
				yield f'{self._path}/{sub_dir_path.name}'
				for path, relative in sub_dir_path.rrglob('*'):
					if self._blacklist.search(relative):
						self.sub_dir_paths.remove(sub_dir_path)
						break
	