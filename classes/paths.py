#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path as PathlibPath
from re import compile as re_compile
from re import Pattern as RePattern

class Path(PathlibPath):
	'''Methods to check and create paths'''

	def str(self):
		'''Return string representation with slashes'''
		return str(self).replace('\\', '/')

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
					return item, regex.pattern
		return None, None

class PathTree:
	'''Tree of paths'''

	def __init__(self, root):
		'''Set up tree'''
		self.path = Path(root).resolve()
		self.name = self.path.name
		self.parent = self.path.parent
		self._subs = tuple(path.str() for path in self.path.rrglob('*'))

	def __str__(self):
		'''Return string representation'''
		return str(self.path)

	def __repr__(self):
		'''Return string representation'''
		return f"Tree('{self.path}')"

	def walk(self):
		'''Return all paths in tree'''
		return self.path.rglob('*')

	def get_relative(self, path):
		'''Return path relative to root'''
		return path.relative_to(self.path)

	def joinpath(self, *args):
		'''Join path with root'''
		return self.path.joinpath(*args)

	def is_accessable_dir(self):
		'''Check if path is an excisting, accessable directory'''
		return self.path.is_accessable_dir()

	def search(self, patterns):
		'''Return first path that matches a pattern'''
		match, pattern = RegEx(patterns).search(self._subs)
		if match:
			return self.path.parent / match, pattern
		return None, None

	def too_long(self, max_len):
		'''Return path that violates given path length (in chars)'''
		for sub in self._subs:
			length = len(sub)
			if length > max_len:
				return self.path.parent / sub, length
		return None, None

	def mk(self):
		'''Create directory'''
		if not self.path.is_accessable_dir():
			self.path.mkdir(parents=True)
			return True
		return False

	def write_text_file(self, filename, text):
		'''Write text to file'''
		return self.path.joinpath(filename).write_text(text, encoding='utf-8')
