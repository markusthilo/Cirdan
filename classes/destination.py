#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.regex import RegEx

class Destination:
	'''Destination class'''

	def __init__(self, path, whitelist, blacklist):
		'''Destination settings'''
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
				yield f'{self._path}/{sub_dir_path.name}'
				if self._whitelist:
					for white_path, white_relative in sub_dir_path.rrglob('*'):
						if self._whitelist.search(white_relative):
							self.sub_dir_paths.append(sub_dir_path)
							if self._blacklist:
								for black_path, black_relative in sub_dir_path.rrglob('*'):
									if self._blacklist.search(black_relative):
										self.sub_dir_paths.pop()
										break
							break
