#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from re import compile as re_compile
from re import Pattern as RePattern

class Path(Path):
	'''Methods to check and create paths'''

	def str(self):
		'''Return string representation with slashes'''
		return str(self).replace('\\', '/')

	def lookup(self):
		'''Return resolved path if existing, else None'''
		path = self.resolve()
		if path.exists():
			return path

	def is_accessable_dir(self):
		'''Check if path is accessable'''
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
			yield path.relative_to(resolved.parent)

class RegEx:
	'''Regular expression for iterable data'''

	def __init__(self, patterns):
		'''Set up checker'''
		self._compiled = tuple(re_compile(pattern) for pattern in patterns)

	def search(self, iterable):
		'''Return first matching item'''
		for item in iterable:
			for regex in self._compiled:
				if regex.search(item):
					return regex.pattern, item
		return None, None

class SourcePath:
	'''Source path to copy'''

	def __init__(self, src_dir):
		'''Set up checker'''
		src_path = src_dir if isinstance(src_dir, Path) else Path(src_dir)
		self.path = src_path.lookup()
		self._subs = tuple(path.str() for path in self.path.rrglob('*')) if self.path else tuple()

	def exists(self):
		'''Return True if path exists'''
		return bool(self.path)

	def search(self, patterns):
		'''Return first path that matches a pattern'''
		return RegEx(patterns).search(self._subs)

	def too_long(self, max_len):
		'''Return path that violates given path length (in chars)'''
		for sub in self._subs:
			if len(sub) > max_len:
				return sub

class DestinationPath:
	'''Destination path to copy to'''

	def __init__(self, src_path, dst_root_path):
		'''Create destination subdir'''
		self.path = dst_root_path.joinpath(dst_root_path, src_path.name)
		if self.path.is_dir():
			self._subs = tuple(path.str() for path in self.path.rrglob('*'))
		elif self.path.exists():
			raise FileExistsError(f'{self.path} is a file')
		else:
			self.path.mkdir(parents=True)
			self._subs = tuple()

	def search(self, patterns):
		'''Return first path that matches a pattern'''
		res = RegEx(patterns).search(self._subs)
		return Path(res) if res else None
