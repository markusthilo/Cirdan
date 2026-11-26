#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from datetime import datetime
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

	def delete_trigger(self, todo: dict, top_dir_name: str) -> None:
		"""Delete trigger file if given"""
		if filename := todo.get("delete_name"):
			self.path.joinpath(top_dir_name, filename).unlink(missing_ok=True)

	def write_trigger(self, todo: dict, top_dir_name: str) -> None:
		"""Write trigger file if given"""
		if filename := todo.get("trigger_name"):
			self.path.joinpath(top_dir_name).write_text_file(filename, self._settings.id)

	def write_todo(self, todo: dict, top_dir_name: str) -> None:
		"""Write todo file if given"""
		if filename := todo.get("todo_name"):
			if task := todo.get("task"):
				self.path.joinpath(top_dir_name).write_text_file(filename, task)

	def write_meta(self, todo: dict, source: Source) -> None:
		"""Write meta file if given"""
		if filename := todo.get("meta_name"):
			directories = dict[str, dict[str, int]]()
			for sub_dir_name, values in source.sub_dirs.items():
				directories[sub_dir_name] = {
					"bytes": values.get("size").integer(),
					"files": values.get("files")
				}
				if "paths_count" in values:
					directories[sub_dir_name]["paths_count"] = values.get("paths_count")
			json = dumps({
				source.name: {
					"bytes": source.size.integer(),
					"files": source.file_cnt,
					"directories": directories,
					"upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				}
			}, indent=4)
			self.path.joinpath(source.name).write_text_file(filename, json, use_strftime=True)
