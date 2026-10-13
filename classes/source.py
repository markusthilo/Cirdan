#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Generator, Callable
from classes.path import Path
from classes.regex import RegEx
from classes.size import Size
if TYPE_CHECKING:
	from classes.settings import Settings
	from threading import Event

class Source:
	"""Source directory"""

	def __init__(self, path: Path, settings: Settings) -> None:
		self.path = path
		self._settings = settings
		self._whitelist = RegEx(self._settings.source_whitelist) if self._settings.source_whitelist else None
		self._blacklist = RegEx(self._settings.source_blacklist) if self._settings.source_blacklist else None
		self._countlist = RegEx(self._settings.count_paths) if self._settings.count_paths else None
		self.counted_paths = {pattern: 0 for pattern in self._countlist.get_patterns()} if self._countlist else None
		self.files = 0
		self.size = Size(0)
		self.whitelist_match = None

	def __repr__(self) -> str:
		"""Printable path"""
		string = f"{self.path}"
		if self.files is not None:
			string += ", 1 File" if self.files == 1 else f", {self.files} Files"
		if self.size is not None:
			string += f", {self.size}"
		return string

	def check(self,
		kill: Event | None = None,
		echo: Callable[..., None] = print,
	) -> Generator[tuple[Path, int | str | None], None, None]:
		"""Check source directory tree"""
		self.whitelist_match = False
		self.files = 0
		self.size = Size(0)
		for path, relative in self.path.rrglob("*"):
			if kill and kill.is_set():
				break
			echo(f"{self._settings.labels.checking} {relative}")
			if self._whitelist and self._whitelist.search(relative):
				self.whitelist_match = True
			if not self._settings.tolerant:
				if self._settings.max_path_length and len(relative) > self._settings.max_path_length:
					yield path, len(relative)
				if self._blacklist:
					if pattern := self._blacklist.search(relative):
						yield path, pattern
			if path.is_file():
				self.files += 1
				self.size += path.get_filesize()
				if self._countlist:
					if pattern := self._countlist.search(relative):
						self.counted_paths[pattern] += 1
			yield path, None
