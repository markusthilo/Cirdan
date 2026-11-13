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
		self.sub_file_extensions = settings.source_sub_file_extensions
		self.top_dir_name: str | None = None
		self.top_dir_path: Path | None = None
		self.sub_dirs = list[tuple[Path, Size, int]]()
		self.sub_files = list[tuple[Path, Size]]()
		self.wished_paths = list[Path]()
		self.counted_paths = dict[str, dict[str, int]]()
		self.file_cnt = 0
		self.size = Size(0)

	def __repr__(self) -> str | None:
		"""Printable path"""
		string = self.top_dir_name if self.top_dir_name else "Name not set"
		string += f" ({self.size}, {self.file_cnt} file(s))\n"
		if self.top_dir_path:
			string += f" -> {self.top_dir_path}\n"
		for sub_dir in self.sub_dirs:
			string += f"    {sub_dir[0].name} ({sub_dir[1]}, {sub_dir[2]} file(s))\n"
		for sub_file in self.sub_files:
			string += f"    {sub_file[0].name} ({sub_file[1]})\n"
		string += "wished_paths\n"
		if self.wished_paths:
			for wished_path in self.wished_paths:
				string += f"    {wished_path.name}\n"
		else:
			string += "    no wished paths\n"
		string += "counted_paths\n"
		if self.counted_paths:
			for counted_path in self.counted_paths:
				string += f"    {counted_path[0].name} ({counted_path[1]} file(s))\n"
				for counted_path_pattern in counted_path[2]:
					string += f"        {counted_path_pattern} ({counted_path[2][counted_path_pattern]} file(s))\n"
		else:
			string += "    no counted paths\n"
		return string

	def set_no_check(self) -> None:
		"""Ignore black-/whitelists and path length"""
		self.top_dir_whitelist = None
		self.sub_dir_whitelist = None
		self.sub_wishlist = None
		self.blacklist = None
		self.sub_file_extensions = None
		self.max_path_length = None

	def top_dir(self, path: Path | str) -> Path | None:
		"""Check if path is top path"""
		path = Path(path).resolve()
		if not path.is_dir():
			raise NotADirectoryError(self._labels.not_a_directory.replace("#", str(path)))
		if not self.top_dir_whitelist:
			return path
		if self.top_dir_whitelist.search(Path(path).name):
			return path
	
	def sub_dir(self, path: Path | str) -> Path | None:
		"""Check if path is sub path"""
		print(f"{path=} {type(path)=}")
		path = Path(path).resolve()
		if not path.is_dir():
			raise NotADirectoryError(self._labels.not_a_directory.replace("#", str(path)))
		if not self.sub_dir_whitelist:
			return path
		if self.sub_dir_whitelist.search(Path(path).name):
			return path

	def sub_file(self, path: Path | str) -> Path | None:
		"""Check if path is sub file"""
		path = Path(path).resolve()
		if not path.is_file():
			raise FileNotFoundError(self._labels.file_not_found.replace("#", str(path)))
		if not self.sub_file_extensions:
			return path
		if path.suffix in self.sub_file_extensions:
			return path

	def add_sub_dir(self, path: Path | str, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Check directory tree; yield (path, length) or (path, blacklist pattern)"""
		path = self.sub_dir(path)
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
				file_cnt += 1
				self.file_cnt += 1
				file_size = abs_path.get_filesize()
				size += file_size
				self.size += file_size
				yield abs_path, None
		self.sub_dirs.append((path, size, file_cnt))

	def add_sub_file(self, path: Path | str) -> None:
		"""Add sub file"""
		sub_file_path = self.sub_file(path)
		if not sub_file_path:
			raise ValueError(self._labels.not_a_valid_file.replace("#", str(path)))
		size = sub_file_path.get_filesize()
		self.file_cnt += 1
		self.size += size
		self.sub_files.append((sub_file_path, size))
		if self.sub_wishlist and self.sub_wishlist.search(sub_file_path.name):
			self.wished_paths.append(sub_file_path)

	def set_top_dir(self, dir_name: str) -> str:
		"""Set top level dir"""
		if self.top_dir_whitelist and not self.top_dir_whitelist.search(dir_name):
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(dir_name)))
		self.top_dir_name = dir_name
		self.top_dir_path = None
		return dir_name

	def insert_top_dir(self, path: Path | str, kill: Event | None = None) -> Generator[tuple[Path, int | str], None, None]:
		"""Set full top level dir"""
		self.top_dir_path = self.top_dir(path)
		if not self.top_dir_path:
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))
		self.top_dir_name = self.top_dir_path.name
		for path in self.top_dir_path.iterdir():
			if path.is_dir():
				for abs_path, value in self.add_sub_dir(path, kill):
					yield abs_path, value
			elif path.is_file():
				self.add_sub_file(path)

	def set(self, path: Path | str) -> Generator[tuple[Path, int | str], None, None]:
		"""Set source by top or sub directory"""
		top_dir_path = self.top_dir(path)
		if top_dir_path:
			for abs_path, value in self.insert_top_dir(top_dir_path):
				yield abs_path, value
		else:
			sub_dir_path = self.sub_dir(path)
			if sub_dir_path:
				for abs_path, value in self.add_sub_dir(sub_dir_path):
					yield abs_path, value
			else:
				raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))