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

	def str(self):
		'''Return string representation with slashes'''
		return str(self).replace('\\', '/')

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
			yield path.relative_to(resolved.parent)

	def open_w(self):
		'''Open file to write utf-8 text'''
		return self.open(mode='w', encoding='utf-8')

class PathTree(Path):
	'''Tree of paths'''

	def search(self, patterns):
		'''Return first path that matches a pattern'''
		compiled = tuple(re_compile(pattern) for pattern in patterns)
		for rel_path in self.rrglob('*'):
			rel_str = rel_path.str()
			for regex in compiled:
				if regex.search(rel_str):
					return self.parent / rel_path, regex.pattern
		return None, None

	def too_long(self, max_len):
		'''Return path that violates given path length (in chars)'''
		for rel_path in self.rrglob('*'):
			length = len(rel_path.str())
			if length > max_len:
				return self.parent / rel_path, length
		return None, None

	def walk_files(self):
		'''Find all files, get raletive paths and file sizes'''
		self.rel_file_paths = list()
		self.file_sizes = list()
		self.total_files = 0
		self.total_bytes = Size(0)
		for rel_path in self.rrglob('*'):
			path = self.parent / rel_path
			if path.is_file():
				self.rel_file_paths.append(rel_path)
				size = path.get_filesize()
				self.file_sizes.append(size)
				self.total_files += 1
				self.total_bytes += size
		return self.total_files

	def get_rel_paths_sizes(self):
		'''Return relative paths and file sizes'''
		yield from zip(self.rel_file_paths, self.file_sizes)

	def mk(self):
		'''Create directory'''
		if not self.is_accessable_dir():
			self.mkdir(parents=True)
			return True
		return False

	def check_file(self, rel_path):
		'''Check if file exists and return size'''
		path = self.parent / rel_path
		if path.is_file():
			return path.get_filesize()

	def write_text_file(self, filename, text):
		'''Write text to file'''
		return self.joinpath(filename).write_text(text, encoding='utf-8')
