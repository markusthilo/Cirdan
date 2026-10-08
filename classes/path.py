#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path as PathlibPath
from time import strftime
from classes.size import Size

class Path(PathlibPath):
	"""Methods to check and create paths"""

	if not hasattr(PathlibPath, 'copy'):	# check if pathlib.Path has copy method
		def copy(self, destination: Path) -> Path:
			"""Add copy method if not exists (Python < 3.14)"""
			destination.write_bytes(self.read_bytes())
			return destination

	def __repr__(self):
		"""Return string representation with slashes"""
		return self.as_posix()

	def timed(self, fmt="%y%m%d_%H%M%S_%n") -> Path:
		"""Return path with timestamp added to name"""
		return self.with_name(strftime(fmt.replace("%n", self.name)))

	def append_name(self, name: str, use_strftime: bool = False) -> Path:
		"""Append name to path"""
		return self.joinpath(strftime(f'{name}')) if use_strftime else self.joinpath(name)

	def get_filesize(self):
		"""Return size of file"""
		return Size(self.stat().st_size)

	def is_accessable_dir(self):
		"""Check if path is accessable (necessary due to bad results with .is_dir() in AD environment)"""
		if not self.is_dir():
			return False
		try:
			self.iterdir()
		except:
			return False
		return True

	def rrglob(self, pattern, case_sensitive=None, recurse_symlinks=False):
		"""Recursive glob that gives paths relative to parent"""
		resolved = self.resolve()
		for path in resolved.rglob(pattern, case_sensitive=case_sensitive, recurse_symlinks=recurse_symlinks):
			yield path, path.relative_to(resolved.parent).as_posix()

	def open_w(self):
		"""Open file to write utf-8 text"""
		return self.open(mode="w", encoding="utf-8")

	def mk(self):
		"""Create directory"""
		if not self.is_accessable_dir():
			self.mkdir(parents=True)
			return True
		return False

	def write_text_file(self, filename, text, use_strftime=False):
		"""Write text to file"""
		return self.append_name(filename, use_strftime=use_strftime).write_text(text, encoding="utf-8")
