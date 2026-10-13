#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Callable
from json import load
from classes.path import Path
from classes.regex import RegEx
if TYPE_CHECKING:
	from classes.settings import Settings

class Destination:
	"""Class to check existing destination directory"""

	def __init__(self,
		settings: Settings,
		name: str,
		path: Path | None = None
	) -> None:
		self._settings = settings
		self.name = name
		if self.name not in self._settings.destinations:
			raise ValueError(f"Destination {self.name} not found in config")
		self.path = Path(path).resolve() if path else Path(self._settings.__dict__[self._settings.destinations[name]["path"]]).resolve()
		self.sub_dir_paths = list[Path]()
		self.todos = self._settings.todo[self._settings.destinations[self.name]["todo"]]
		self.do_nothing = None
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
		"""Check destination directory and return list of sub directories that might be triggered"""
		self.sub_dir_paths = list[Path]()
		for sub_dir_path in self.path.iterdir():
			if sub_dir_path.is_dir():
				try:
					with sub_dir_path.joinpath(self._settings.halted_name).open(encoding="utf-8") as fp:
						items = load(fp)
						if items["username"] == username:
							self.sub_dir_paths.append(sub_dir_path)
				except:
					pass
		self.sub_dir_paths.sort(key=lambda path: path.name)
		return self.sub_dir_paths

	def delete_trigger(self, todo: str, sub_dir_path: Path) -> None:
		"""Delete trigger file if given"""
		if filename := self.todos[todo]["delete_name"]:
			sub_dir_path.joinpath(filename).unlink(missing_ok=True)

	def count_paths(self, sub_dir_path: Path, echo: Callable[..., None] = print) -> Generator[str, None, None]:
		"""Count paths given by "count_paths" RegEx patterns in sub directory"""
		if self._countlist:
			counted_paths = {pattern: 0 for pattern in self._countlist.get_patterns()}
			for path, relative in sub_dir_path.rrglob("*"):
				if pattern := self._countlist.search(relative):
					counted_paths[pattern] += 1
				echo(f"{self._settings.labels.checking} {relative}")
			return counted_paths

	def write_meta(self, todo: str, sub_dir_path: Path, counted_paths: dict[str, int]) -> None:
		"""Write meta file if given"""
		if self.todos[todo]["meta_name"]:
			if "%p" in self.todos[todo]["meta_content"]:
				json = "{\n"
				for pattern, n in counted_paths.items():
					json += f'        {{"pattern": "{pattern}", "matches": {n}}}\n'
				json += "    }"
				content = self.todos[todo]["meta_content"].replace("%p", json)
			else:
				content = self.todos[todo]["meta_content"]
			sub_dir_path.write_text_file(self.todos[todo]["meta_name"], content, use_strftime=True)

	def write_trigger(self, todo: str, sub_dir_path: Path) -> None:
		"""Write trigger file if given"""
		if self.todos[todo]["trigger_name"]:
			sub_dir_path.write_text_file(self.todos[todo]["trigger_name"], self._settings.id)
