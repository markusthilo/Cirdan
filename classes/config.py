#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import executable as __executable__
from json import load
from platform import system
from pprint import pformat
from classes.path import Path
from classes.destination import Destination

__app_path__ = Path(__file__).parent.parent if Path(__executable__).name.startswith('python') else Path(__executable__).parent

class Config:
	"""Configuration from JSON file"""

	def __init__(self, path: str | Path | None = None):
		self.app_path = __app_path__
		self.system = system()
		path = Path(path).resolve() if path else self.app_path.joinpath("config.json")
		with path.open(encoding="utf-8") as fp:
			for key, value in load(fp).items():
				if key == "paths":
					for path_key, path_value in value[self.system].items():
						self.__dict__[path_key] = self._resolve_path(path_value)
				else:	
					self.__dict__[key] = value
		self.accessible_destinations = dict[str, Destination]()
		for dst_name in self.destinations:
			dst = Destination(self, dst_name)
			if dst.is_accessible():
				self.accessible_destinations[dst_name] = dst

	def _resolve_path(self, path_value: str) -> Path:
		"""Expand $HOME / $APP prefixes (case-insensitive) and resolve"""
		normalized = path_value.replace("\\", "/")
		upper = normalized.upper()
		if upper.startswith("$HOME/"):
			return Path().home().joinpath(normalized[6:]).resolve()
		if upper.startswith("$APP/"):
			return self.app_path.joinpath(normalized[5:]).resolve()
		return Path(path_value).resolve()

	def __repr__(self) -> str:
		"""Readable key/value listing of the loaded configuration"""
		lines = ["Config:"]
		width = max((len(key) for key in self.__dict__), default=0)
		for key, value in self.__dict__.items():
			formatted = pformat(value, width=76, sort_dicts=False)
			if "\n" in formatted:
				indented = formatted.replace("\n", "\n" + " " * (width + 3))
				lines.append(f"  {key:<{width}} = {indented}")
			else:
				lines.append(f"  {key:<{width}} = {formatted}")
		return "\n".join(lines)
