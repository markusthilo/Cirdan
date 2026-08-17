#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.path import Path
from classes.regex import RegEx
from classes.size import Size
from classes.logger import Logger as Log

class Source:
	'''Source directory'''

	def __init__(self, directory, max_path_len=None, whitelist=None, blacklist=None):
		'''Initialize source directory object'''
		self.path = Path(directory)
		self.name = self.path.name
		self.max_path_len = max_path_len
		self.whitelist = RegEx(whitelist) if whitelist else None
		self.blacklist = RegEx(blacklist) if blacklist else None
		self.files = None
		self.size = Size(0)
		self.whitelist_match = False

	def __repr__(self):
		'''Printable path'''
		string = f'{self.path}'
		if self.files:
			string += ', 1 File' if len(self.files) == 1 else f', {len(self.files)} Files'
		if self.size:
			string += f', {self.size.readable()}'
		return string

	def check(self):
		'''Check source directory tree'''
		self.whitelist_match = False
		self.files = list()
		self.size = Size(0)
		for path, relative in self.path.rrglob('*'):
			if self.whitelist and self.whitelist.search(relative):
				self.whitelist_match = True
			if self.max_path_len and len(relative) > self.max_path_len:
				yield path, len(relative)
			if self.blacklist:
				if pattern := self.blacklist.search(relative):
					yield path, pattern
			if path.is_file():
				size = path.get_filesize()
				self.files.append({'path': path, 'relative': relative, 'size': size})
				self.size += size
			yield path, None
