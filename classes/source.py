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
		self.top_dir_whitelist = RegEx(settings.source_top_dir_whitelist) if settings.source_top_dir_whitelist else None
		self.sub_dir_whitelist = RegEx(settings.source_sub_dir_whitelist) if settings.source_sub_dir_whitelist else None
		self.sub_wishlist = RegEx(settings.source_sub_wishlist) if settings.source_sub_wishlist else None
		self.blacklist = RegEx(settings.source_blacklist) if settings.source_blacklist else None
		self.countlist = RegEx(settings.count_paths) if settings.count_paths else None
		self.max_path_length = settings.max_path_length
		self.sub_suffixes = settings.source_sub_filetypes.keys()
		self.name: str | None = None
		self.top_dir_path: Path | None = None
		self.sub_dirs = dict[str, dict[str, Path | Size | int]]()
		self.sub_files = dict[str, dict[str, Path | Size]]()
		self.wished_files = dict[str, Path]()
		self.counted_paths = dict[str, dict[str, int]]()
		self.file_cnt = 0
		self.size = Size(0)

	def __repr__(self) -> str | None:
		"""Printable path"""
		string = self.name if self.name else "Name not set"
		string += f" ({self.size}, {self.file_cnt} file(s))\n"
		if self.top_dir_path:
			string += f" -> {self.top_dir_path}\n"
		string += "sub_dirs\n"
		for key, value in self.sub_dirs.items():
			string += f"    {key}: {value}\n"
		string += "sub_files\n"
		for key, value in self.sub_files.items():
			string += f"    {key}: {value}\n"
		string += "wished_files\n"
		for key, value in self.wished_files.items():
			string += f"    {key}: {value}\n"
		string += "counted_paths\n"
		for key, value in self.counted_paths.items():
			string += f"    {key}: {value}\n"
		return string

	def set_no_check(self) -> None:
		"""Ignore black-/whitelists and path length"""
		self.top_dir_whitelist = None
		self.sub_dir_whitelist = None
		self.sub_wishlist = None
		self.blacklist = None
		self.sub_file_extensions = None
		self.max_path_length = None

	def top_dir(self, arg: Path | str) -> str | None:
		"""Check if path is an allowedtop path"""
		path = Path(arg).resolve()
		if not path.is_dir():
			raise NotADirectoryError(self._labels.not_a_directory.replace("#", str(path)))
		if not self.top_dir_whitelist:
			return path
		if self.top_dir_whitelist.search(Path(path).name):
			return path
	
	def sub_dir(self, arg: Path | str) -> Path | None:
		"""Check if path is an allowed sub path"""
		path = Path(arg).resolve()
		if not path.is_dir():
			raise NotADirectoryError(self._labels.not_a_directory.replace("#", str(path)))
		if not self.sub_dir_whitelist:
			return path
		if self.sub_dir_whitelist.search(Path(path).name):
			return path

	def sub_file(self, arg: Path | str) -> Path | None:
		"""Check if path is an allowed sub file"""
		path = Path(arg).resolve()
		if not path.is_file():
			raise FileNotFoundError(self._labels.file_not_found.replace("#", str(path)))
		if not self.sub_suffixes:
			return path
		if path.suffix in self.sub_suffixes:
			return path

	def add_sub_dir(self, arg: Path | str, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Check directory tree; yield (path, length) or (path, blacklist pattern)"""
		path = self.sub_dir(arg)
		if not path:
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))
		size = Size(0)
		file_cnt = 0
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
				file_size = abs_path.get_filesize()
				size += file_size
				self.size += file_size
				file_cnt += 1
				self.file_cnt += 1
				yield abs_path, None
		self.sub_dirs[path.name] = {"path": path, "size": size, "files": file_cnt}
		if self.countlist:
			self.counted_paths[path.name] = counted_paths

	def rm_sub_dir(self, name: str) -> None:
		"""Remove sub directory"""
		sub_dir = self.sub_dirs.pop(name)
		self.size -= sub_dir["size"]
		self.file_cnt -= sub_dir["files"]
		if self.countlist:
			self.counted_paths.pop(name)

	def add_sub_file(self, arg: Path | str) -> None:
		"""Add sub file"""
		path = self.sub_file(arg)
		if not path:
			raise ValueError(self._labels.not_a_valid_file.replace("#", str(arg)))
		size = path.get_filesize()
		self.file_cnt += 1
		self.size += size
		self.sub_files[path.name] = {"path": path, "size": size}
		if self.sub_wishlist and self.sub_wishlist.search(path.name):
			self.wished_files[path.name] = path
		return path.name

	def rm_sub_file(self, name: str) -> None:
		"""Remove sub file"""
		sub_file = self.sub_files.pop(name)
		self.size -= sub_file["size"]
		self.file_cnt -= 1
		if self.sub_wishlist and self.sub_wishlist.search(name):
			self.wished_files.pop(name)

	def set_name(self, name: str) -> str:
		"""Set top level dir"""
		if self.top_dir_whitelist and not self.top_dir_whitelist.search(name):
			raise ValueError(self._labels.not_a_valid_directory.replace("#", name))
		self.name = name
		return name

	def insert_top_dir(self, arg: Path | str, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Set full top level dir"""
		self.top_dir_path = self.top_dir(arg)
		if not self.top_dir_path:
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))
		self.name = self.top_dir_path.name
		for path in self.top_dir_path.iterdir():
			if path.is_dir():
				for abs_path, value in self.add_sub_dir(path, kill):
					yield abs_path, value
			elif path.is_file():
				if self.add_sub_file(path):
					yield path.relative_to(self.top_dir_path), None
