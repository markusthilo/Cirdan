#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Generator
from threading import Event
from classes.path import Path
from classes.regex import RegEx
from classes.size import Size
from classes.settings import Settings

class Source:
	"""Source directory"""

	def __init__(self, path: Path, settings: Settings) -> None:
		self.path = path
		self._settings = settings
		self._whitelist = RegEx(self._settings.source_whitelist) if self._settings.source_whitelist else None
		self._blacklist = RegEx(self._settings.source_blacklist) if self._settings.source_blacklist else None
		self._max_path_length = self._settings.max_path_length
		self._countlist = RegEx(self._settings.count_paths) if self._settings.count_paths else None
		self.counted_paths: dict[str, int] | None = (
			{pattern: 0 for pattern in self._countlist.get_patterns()} if self._countlist else None
		)
		self.files = 0
		self.size = Size(0)
		self.whitelist_match: bool | None = None

	@property
	def name(self) -> str:
		"""Directory name (used as destination subdir)"""
		return self.path.name

	@property
	def whitelist(self) -> RegEx | None:
		"""Configured source whitelist, if any"""
		return self._whitelist

	def __repr__(self) -> str:
		"""Printable path"""
		string = f"{self.path}"
		if self.files is not None:
			string += ", 1 File" if self.files == 1 else f", {self.files} Files"
		if self.size is not None:
			string += f", {self.size}"
		return string

	def disable_path_length_check(self) -> None:
		"""Ignore max path length for the rest of this source check"""
		self._max_path_length = None

	def disable_blacklist(self) -> None:
		"""Ignore blacklist for the rest of this source check"""
		self._blacklist = None

	def check(self, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Check source directory tree; yield (path, length) or (path, blacklist pattern)"""
		self.whitelist_match = False
		self.files = 0
		self.size = Size(0)
		if self._countlist:
			self.counted_paths = {pattern: 0 for pattern in self._countlist.get_patterns()}
		for path, relative in self.path.rrglob("*"):
			if kill and kill.is_set():
				break
			if self._whitelist and self._whitelist.search(relative):
				self.whitelist_match = True
			if not self._settings.no_source_check:
				if self._max_path_length and len(relative) > self._max_path_length:
					yield path, len(relative)
				if self._blacklist:
					if pattern := self._blacklist.search(relative):
						yield path, pattern
			if path.is_file():
				self.files += 1
				try:
					self.size += path.get_filesize()
				except OSError:
					pass
				if self._countlist and self.counted_paths is not None:
					if pattern := self._countlist.search(relative):
						self.counted_paths[pattern] += 1
