#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from json import load, dumps
from classes.path import Path
if TYPE_CHECKING:
	from classes.settings import Settings
	from classes.source import Source

class Destination:
	"""The parent directory for every copy target directory"""

	def __init__(self, settings: Settings) -> None:
		self._settings = settings
		self.name = self._settings.destination_name
		self.path = self._settings.destination_path
		self.todos = self._settings.destination_todos

	def __repr__(self) -> str:
		"""Name"""
		return f"{self.name}"

	def check_sub_dirs(self) -> list[Path]:
		"""Check destination directory and return list of subdirectories that might be triggered"""
		self.sub_dir_paths = list[Path]()
		try:
			entries = list[Path](self.path.iterdir())
		except OSError:
			return self.sub_dir_paths
		for sub_dir_path in entries:
			if not sub_dir_path.is_dir():
				continue
			try:
				with sub_dir_path.joinpath(self._settings.halted_name).open(encoding="utf-8") as fp:
					items = load(fp)
				if items.get("username") == self._settings.username:
					self.sub_dir_paths.append(sub_dir_path)
			except (OSError, ValueError, TypeError, KeyError):
				pass
		self.sub_dir_paths.sort(key=lambda path: path.name)
		return self.sub_dir_paths

	def delete_trigger(self, todo: str, source: Source) -> None:
		"""Delete trigger file if given"""
		if filename := self.todos[todo].get("delete_name"):
			self.path.joinpath(source.name, filename).unlink(missing_ok=True)

	def write_meta(self, todo: str, source: Source) -> None:
		"""Write meta file if given"""
		if filename := self.todos[todo].get("meta_name"):
			meta_content = self.todos[todo].get("meta_content")
			if not meta_content:
				return
			if "%p" in meta_content and source.counted_paths:
				paths_json = dumps(
					{dir_name: {"pattern": pattern, "matches": n}
						for dir_name , pattern, n in source.counted_paths.items()
					}
				)
				meta_content = meta_content.replace("%p", paths_json)
			self.path.joinpath(source.name).write_text_file(filename, meta_content, use_strftime=True)

	def write_trigger(self, todo: str, source: Source) -> None:
		"""Write trigger file if given"""
		if filename := self.todos[todo].get("trigger_name"):
			self.path.joinpath(source.name).write_text_file(filename, self._settings.id)
