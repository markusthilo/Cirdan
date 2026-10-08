#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.path import Path
from classes.regex import RegEx
from classes.size import Size

class Source:
	"""Source directory"""

	def __init__(self,
		directory: Path,
		max_path_len: int | None = None,
		whitelist: str | None = None,
		blacklist: str | None = None,
		countlist: str | None = None
	) -> None:
		self.path = Path(directory)
		self.name = self.path.name
		self.max_path_len = max_path_len
		self.whitelist = RegEx(whitelist) if whitelist else None
		self.blacklist = RegEx(blacklist) if blacklist else None
		self.countlist = RegEx(countlist) if countlist else None
		self.files = None
		self.size = Size(0)
		self.whitelist_match = False

	def __repr__(self) -> str:
		'''Printable path'''
		string = f'{self.path}'
		if self.files:
			string += ', 1 File' if len(self.files) == 1 else f', {len(self.files)} Files'
		if self.size:
			string += f', {self.size}'
		return string

	def check(self) -> Generator[tuple[Path, int | str | None], None, None]:
		'''Check source directory tree'''
		self.whitelist_match = False
		self.files = list()
		self.size = Size(0)
		for path, relative in self.path.rrglob("*"):
			if self.whitelist and self.whitelist.search(relative):
				self.whitelist_match = True
			if self.max_path_len and len(relative) > self.max_path_len:
				yield path, len(relative)
			if self.blacklist:
				if pattern := self.blacklist.search(relative):
					yield path, pattern
			if path.is_file():
				size = path.get_filesize()
				self.files.append({"path": path, "relative": relative, "size": size})
				self.size += size
			yield path, None

	def get_countlist_match(self, relative: str) -> str | None:
		"""Return RegEx pattern from countlist to given relative path"""
		if self.countlist:
			return self.countlist.search(relative)
