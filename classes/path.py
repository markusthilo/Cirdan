#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path as PathlibPath
from time import strftime
from re import compile as re_compile
from classes.size import Size

class Path(PathlibPath):
	'''Methods to check and create paths'''

	if not hasattr(PathlibPath, 'copy'):	# check if pathlib.Path has copy method
		def copy(self, destination):
			'''Add copy method if not exists (Python < 3.14)'''
			destination.write_bytes(self.read_bytes())
			return destination

	if not hasattr(PathlibPath, 'move'):	# check if pathlib.Path has move method
		def move(self, destination):
			'''Add move method if not exists (Python < 3.14)'''
			destination.write_bytes(self.read_bytes())
			self.unlink()
			return destination

	def __repr__(self):
		'''Return string representation with slashes'''
		return self.as_posix()

	def timed(self, fmt='%t_%n'):
		'''Return path with timestamp added to name'''
		return self.with_name(
			fmt.replace('%t', strftime('%y%m%d_%H%M%S')).replace('%n', self.name).replace('%s', self.stem).replace('%x', self.suffix)
		)

	def get_filesize(self):
		'''Return size of file'''
		return Size(self.stat().st_size)

	def is_accessable_dir(self):
		'''Check if path is accessable (necessary due to bad results with .is_dir() in AD environment)'''
		if not self.is_dir():
			return False
		try:
			self.iterdir()
		except:
			return False
		return True

	def rrglob(self, pattern, *, case_sensitive=None, recurse_symlinks=False):
		'''Recursive glob that gives paths relative to parent'''
		resolved = self.resolve()
		for path in resolved.rglob(pattern, case_sensitive=case_sensitive, recurse_symlinks=recurse_symlinks):
			yield path, path.relative_to(resolved.parent).as_posix()

	def open_w(self):
		'''Open file to write utf-8 text'''
		return self.open(mode='w', encoding='utf-8')

	def mk(self):
		'''Create directory'''
		if not self.is_accessable_dir():
			self.mkdir(parents=True)
			return True
		return False

	def write_text_file(self, filename, text):
		'''Write text to file'''
		return self.joinpath(filename).write_text(text, encoding='utf-8')
