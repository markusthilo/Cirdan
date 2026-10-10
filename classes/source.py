#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.path import Path
from classes.regex import RegEx
from classes.size import Size

class Source:
	"""Source directory"""

	def __init__(self, path: Path, config: Config) -> None:
		self.path = path
		self._config = config
		self._whitelist = RegEx(self._config.source_whitelist) if self._config.source_whitelist else None
		self._blacklist = RegEx(self._config.source_blacklist) if self._config.source_blacklist else None
		self._countlist = RegEx(self._config.count_paths) if self._config.count_paths else None
		self.counted_paths = {pattern: 0 for pattern in self._countlist} if self._countlist else None
		self.files = 0
		self.size = Size(0)
		self.whitelist_match = None

	def __repr__(self) -> str:
		"""Printable path"""
		string = f'{self.path}'
		if self.files is not None:
			string += ', 1 File' if self.files == 1 else f', {self.files} Files'
		if self.size is not None:
			string += f', {self.size}'
		return string

	def check(self) -> Generator[tuple[Path, int | str | None], None, None]:
		"""Check source directory tree"""
		self.whitelist_match = False
		self.files = 0
		self.size = Size(0)
		for path, relative in self.path.rrglob("*"):
			if self._whitelist and self._whitelist.search(relative):
				self.whitelist_match = True
			if self._config.max_path_length and len(relative) > self._config.max_path_length:
				yield path, len(relative)
			if self._blacklist:
				if pattern := self._blacklist.search(relative):
					yield path, pattern
			if path.is_file():
				self.files += 1
				self.size += path.get_filesize()
			yield path, None

	def count_paths(self) -> Generator[str, None, None]:
		"""Count paths given by "count_paths" RegEx patterns"""
		if self._countlist:
			for path, relative in self.path.rrglob("*"):
				if pattern := self._countlist.search(relative):
					self.counted_paths[pattern] += 1
				yield relative
		else:
			yield ""