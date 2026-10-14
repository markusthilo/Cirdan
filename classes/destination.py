#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from collections.abc import Callable
from json import load, dumps
from classes.path import Path
from classes.regex import RegEx
if TYPE_CHECKING:
	from classes.settings import Settings

class Destination:
	"""Class to check existing destination directory"""

	def __init__(
		self,
		settings: Settings,
		name: str,
		path: Path | str | None = None,
	) -> None:
		self._settings = settings
		self.name = name
		if self.name not in self._settings.destinations:
			raise ValueError(f"Destination {self.name} not found in config")
		dst_cfg = self._settings.destinations[name]
		path_key = dst_cfg["path"]
		todo_key = dst_cfg["todo"]
		if todo_key not in self._settings.todo:
			raise ValueError(f"Todo set {todo_key!r} not found in config")
		self.path = Path(path).resolve() if path else Path(getattr(self._settings, path_key)).resolve()
		self.sub_dir_paths: list[Path] = []
		self.todos = self._settings.todo[todo_key]
		self.do_nothing: str | None = None
		for key, value in self.todos.items():
			if not value["do_something"]:
				self.do_nothing = key
				break
		self._countlist = RegEx(self._settings.count_paths) if self._settings.count_paths else None

	def __repr__(self) -> str:
		"""Name"""
		return f"{self.name}"

	def is_accessible(self) -> bool:
		"""Check if destination directory exists and is accessible"""
		return self.path.is_accessible()

	def check_sub_dirs(self, username: str) -> list[Path]:
		"""Check destination directory and return list of subdirectories that might be triggered"""
		self.sub_dir_paths = []
		try:
			entries = list(self.path.iterdir())
		except OSError:
			return self.sub_dir_paths
		for sub_dir_path in entries:
			if not sub_dir_path.is_dir():
				continue
			try:
				with sub_dir_path.joinpath(self._settings.halted_name).open(encoding="utf-8") as fp:
					items = load(fp)
				if items.get("username") == username:
					self.sub_dir_paths.append(sub_dir_path)
			except (OSError, ValueError, TypeError, KeyError):
				pass
		self.sub_dir_paths.sort(key=lambda path: path.name)
		return self.sub_dir_paths

	def delete_trigger(self, todo: str, sub_dir_path: Path) -> None:
		"""Delete trigger file if given"""
		if filename := self.todos[todo].get("delete_name"):
			sub_dir_path.joinpath(filename).unlink(missing_ok=True)

	def count_paths(self, sub_dir_path: Path, echo: Callable[..., None] = print) -> dict[str, int]:
		"""Count paths given by "count_paths" RegEx patterns in sub directory"""
		if not self._countlist:
			return {}
		counted_paths = {pattern: 0 for pattern in self._countlist.get_patterns()}
		for path, relative in sub_dir_path.rrglob("*"):
			if pattern := self._countlist.search(relative):
				counted_paths[pattern] += 1
			echo(f"{self._settings.labels.checking} {relative}")
		return counted_paths

	def write_meta(self, todo: str, sub_dir_path: Path, counted_paths: dict[str, int] | None = None) -> None:
		"""Write meta file if given"""
		todo_cfg = self.todos[todo]
		meta_name = todo_cfg.get("meta_name")
		meta_content = todo_cfg.get("meta_content")
		if not meta_name or meta_content is None:
			return
		if "%p" in meta_content:
			paths_json = dumps(
				[{"pattern": pattern, "matches": n} for pattern, n in (counted_paths or {}).items()],
				indent=8,
			)
			content = meta_content.replace("%p", paths_json)
		else:
			content = meta_content
		sub_dir_path.write_text_file(meta_name, content, use_strftime=True)

	def write_trigger(self, todo: str, sub_dir_path: Path) -> None:
		"""Write trigger file if given"""
		if filename := self.todos[todo].get("trigger_name"):
			sub_dir_path.write_text_file(filename, self._settings.id)
