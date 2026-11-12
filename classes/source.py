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

	def __init__(self, settings: Settings) -> None:
		self._labels = settings.labels
		self.top_whitelist = RegEx(settings.source_top_whitelist) if settings.source_top_whitelist else None
		self.sub_whitelist = RegEx(settings.source_sub_whitelist) if settings.source_sub_whitelist else None
		self.sub_wishlist = RegEx(settings.source_sub_wishlist) if settings.source_sub_wishlist else None
		self.blacklist = RegEx(settings.source_blacklist) if settings.source_blacklist else None
		self.countlist = RegEx(settings.count_paths) if settings.count_paths else None
		self.max_path_length = settings.max_path_length
		self.top_path = None
		self.sub_dirs = dict[str, tuple[int, Size, dict[str, int] | None]]()
		self.sub_files = list[Path]()
		self.wished_paths = list[Path]()
		self.files = 0
		self.size = Size(0)
		self.whitelist_match: bool | None = None

	def __repr__(self) -> str:
		"""Printable path"""
		string = f"{self.path}"
		if self.files is not None:
			string += ", 1 File" if self.files == 1 else f", {self.files} Files"
		if self.size is not None:
			string += f", {self.size}"
		return string

	def set_no_check(self) -> None:
		"""Ignore black-/whitelists and path length"""
		self.top_whitelist = None
		self.sub_whitelist = None
		self.sub_wishlist = None
		self.blacklist = None
		self.max_path_length = None

	def is_top_dir(self, path: Path | str) -> bool:
		"""Check if path is top path"""
		return self.top_whitelist and self.top_whitelist.search(Path(path).name)
	
	def is_sub_dir(self, path: Path | str) -> bool:
		"""Check if path is sub path"""
		return self.sub_whitelist and self.sub_whitelist.search(Path(path).name)

	def add_sub_dir(self, path: Path | str, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Check source directory tree; yield (path, length) or (path, blacklist pattern)"""
		path = Path(path).resolve()
		if not path.is_dir():
			raise NotADirectoryError(self._labels.not_a_directory.replace("#", str(path)))
		if not self.is_sub_path(path):
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))
		file_cnt = 0
		size = Size(0)
		counted_paths = {pattern: 0 for pattern in self.countlist.get_patterns()} if self.countlist else None
		for abs_path, rel_path in path.rrglob("*"):
			if kill and kill.is_set():
				break
			if self.blacklist:
				if pattern := self.blacklist.search(rel_path):
					yield abs_path, pattern
			if self.max_path_length:
				path_length = len(rel_path)
				if path_length > self.max_path_length:
					yield abs_path, path_length
			if self.countlist:
				if pattern := self.countlist.search(rel_path):
					counted_paths[pattern] += 1
			if abs_path.is_file():
				file_cnt += 1
				size += abs_path.get_filesize()
				yield abs_path, None
		self.sub_dirs[path.name] = file_cnt, size, counted_paths

	def add_sub_file(self, path: Path | str) -> None:
		"""Add sub file"""
		path = Path(path).resolve()
		if not path.is_file():
			raise FileNotFoundError(self._labels.file_not_found.replace("#", str(path)))
		self.sub_files.append(path)
		if self.sub_wishlist and self.sub_wishlist.search(path.name):
			self.wished_paths.append(path)

	def set_top_dir(self, path: Path | str) -> None:
		"""Set full top level dir"""
		self.top_path = Path(path).resolve()
		for path in self.top_path.iterdir():
			for abs_path, value in self.add_sub_path(path):
				yield abs_path, value
