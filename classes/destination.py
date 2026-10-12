#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from json import load
from classes.path import Path

if TYPE_CHECKING:
	from classes.config import Config

class Destination:
	"""Class to check existing destination directory"""

	def __init__(self,
		config: Config,
		name: str,
		path: Path | None = None
	) -> None:
		self.name = name
		self._config = config
		if name not in self._config.destinations:
			raise ValueError(f"Destination {name} not found in config")
		self.path = Path(path).resolve() if path else Path(self._config.__dict__[self._config.destinations[name]["path"]]).resolve()
		self.sub_dir_paths = list[Path]()
		self.todos = self._config.todo[self._config.destinations[name]["todo"]]

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
				if halted_path := sub_dir_path.joinpath(self._config.halted_name).is_file():
					try:
						with halted_path.open(encoding="utf-8") as fp:
							items = load(fp)
							if items["username"] == username:
								self.sub_dir_paths.append(sub_dir_path)
					except:
						pass
		return self.sub_dir_paths

	def delete_trigger(self, todo: str, sub_dir_path: Path) -> None:
		"""Delete trigger file if given"""
		if filename := self.todos[todo]["delete_name"]:
			sub_dir_path.joinpath(self.delete_name).unlink(missing_ok=True)

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

	def write_trigger(self, todo: str, sub_dir_path: Path, id: str) -> None:
		"""Write trigger file if given"""
		if self.todos[todo]["trigger_name"]:
			sub_dir_path.write_text_file(self.todos[todo]["trigger_name"])
