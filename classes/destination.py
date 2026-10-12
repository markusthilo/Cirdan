#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from json import load
from classes.path import Path

if TYPE_CHECKING:
	from classes.settings import Settings

class Destination:
	"""Class to check existing destination directory"""

	def __init__(self,
		settings: Settings,
		name: str,
		path: Path | None = None
	) -> None:
		self.name = name
		self._config = settings.config
		if name not in self._config.destinations:
			raise ValueError(f"Destination {name} not found in config")
		self._settings = settings
		self.path = Path(path).resolve() if path else Path(self._config.__dict__[self._config.destinations[name]["path"]]).resolve()
		self.sub_dir_paths = list[Path]()

	def __repr__(self) -> str:
		"""Printable destination is parent and name of path"""
		return f"{self.name}: {self.path}"

	def is_accessible(self) -> bool:
		"""Check if destination directory exists and is accessible"""
		return self.path.is_accessible()

	def check_sub_dirs(self) -> list[Path]:
		"""Check destination directory and return list of sub directories that might be triggered"""
		self.sub_dir_paths = list[Path]()
		for sub_dir_path in self.path.iterdir():
			if sub_dir_path.is_dir():
				if halted_path := sub_dir_path.joinpath(self._config.halted_name).is_file():
					try:
						with halted_path.open(encoding="utf-8") as fp:
							items = load(fp)
							if items["username"] == self._settings.username:
								self.sub_dir_paths.append(sub_dir_path)
					except:
						pass
		return self.sub_dir_paths
