#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any
from sys import executable
from platform import node, system
from json import load, dump
from getpass import getuser
from pprint import pformat
from types import SimpleNamespace
from classes.path import Path

__executable__ = Path(executable)
__app_path__ = (
	Path(__file__).parent.parent
	if __executable__.name.startswith("python")
	else __executable__.parent
)
__system__ = system()

class Config:
	"""Load static configuration from file"""

	def __init__(self, path: Path | str | None = None) -> None:
		path = Path(path).resolve() if path else __app_path__.joinpath("config.json")
		self._repr_name = "Config"
		with path.open(encoding="utf-8") as fp:
			for key, value in load(fp).items():
				if key == "paths":
					for path_key, path_value in value[__system__].items():
						self.__dict__[path_key] = self._resolve_path(path_value)
				else:
					self.__dict__[key] = value

	def _resolve_path(self, path_value: str) -> Path:
		"""Expand $HOME / $APP prefixes (case-insensitive) and resolve"""
		normalized = path_value.replace("\\", "/")
		upper = normalized.upper()
		if upper.startswith("$HOME/"):
			return Path().home().joinpath(normalized[6:]).resolve()
		if upper.startswith("$APP/"):
			return __app_path__.joinpath(normalized[5:]).resolve()
		return Path(path_value).resolve()

	def __repr__(self) -> str:
		"""Readable key/value listing"""
		lines = [f"{self._repr_name}:"]
		width = max((len(key) for key in self.__dict__.keys()), default=0)
		for key in self.__dict__.keys():
			value = self.__dict__[key] if key in self.__dict__ else None
			formatted = pformat(value, width=76, sort_dicts=False)
			if "\n" in formatted:
				indented = formatted.replace("\n", "\n" + " " * (width + 3))
				lines.append(f"  {key:<{width}} = {indented}")
			else:
				lines.append(f"  {key:<{width}} = {formatted}")
		return "\n".join(lines)

class Settings(Config):
	"""User settings, configuration and labels"""

	def __init__(self,
		version: str = "2_Under_Construction",
		config: Path | None = None,
		source_name: str | None = None,
		destination_name: str | None = None,
		destination_path: Path | str | None = None,
		no_source_check: bool = False,
		todo: str | None = None,
		username: str | None = None,
		mail_to: str | None = None,
		mail_subject: str | None = None,
		user_log: Path | None = None
	) -> None:
		self.version = version
		self.app_path = __app_path__
		self.system = __system__
		self._repr_name = "Settings"
		self.hostname = node()
		try:
			super().__init__(config)
		except:
			raise ValueError(f"Failed to load configuration from {config}")
		try:
			with self.labels_path.open(encoding="utf-8") as fp:
				self.labels = SimpleNamespace(**load(fp))
		except:
			raise ValueError(f"Failed to load labels from {self.labels_path}")
		self._path = self.local_path / self.settings_name
		try:
			with self._path.open(encoding="utf-8") as fp:
				items: dict[str, Any] = load(fp)
		except:
			items = {}
			try:
				self.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		self.source_name = source_name
		if destination_path:
			if not destination_name:
				raise ValueError(self.labels.destination_name_required)
			self.destination_arg_set = True
			self.set_destination(destination_name)
			self.destination_path = Path(destination_path).resolve()
			if not self.destination_path.is_accessible():
				raise ValueError(self.labels.destination_not_accessible.replace("#", destination_name))
			self.accessible_destinations = {self.destination_name: self.destination_path}
		else:
			self.destination_arg_set = False
			self.accessible_destinations = dict[str, Path]()
			for dst_name, dst_values in self.destinations.items():
				dst_path = self.__dict__.get(dst_values["path"]).resolve()
				if dst_path.is_accessible():
					self.accessible_destinations[dst_name] = dst_path
			if not self.accessible_destinations:
				raise ValueError(self.labels.no_accessible_destination)
			if len(self.accessible_destinations) == 1:
				self.set_destination(next(iter(self.accessible_destinations.keys())))
			else:
				self.destination_name = items.get("destination")
				if self.destination_name in self.accessible_destinations:
					self.set_destination(self.destination_name)
				else:
					self.destination_name = None
					self.destination_path = None
					self.destination_todos = None
					self.destination_do_nothing = None
		self.selected_todo = todo if self.destination_todos and todo in self.destination_todos.keys() else None
		self.no_source_check = no_source_check
		self.username = username or items.get("username") or getuser()
		self.sendmail = bool(mail_to) or items.get("sendmail", False)
		self.mail_to = mail_to or items.get("mail_to", "")
		self.mail_subject = mail_subject or items.get("mail_subject") or self.mail["default-subject"]
		self.gui_geometry = items.get("gui_geometry", "")
		self.user_log = user_log
		self.id = f'{{\n  "hostname": "{self.hostname}",\n  "username": "{self.username}"\n}}'

	def set_destination(self, destination_name: str | None) -> None:
		"""Set selected destination"""
		self.destination_name = destination_name
		self.destination_path = self.accessible_destinations.get(destination_name) if destination_name else None
		self.destination_todos = self.todo.get(self.destinations[destination_name]["todo"]) if destination_name else None
		self.destination_do_nothing = None
		for todo, values in self.destination_todos.items():
			if values.get("do_something") == False:
				self.destination_do_nothing = todo
				break

	def set_todo(self, todo: str | None) -> None:
		"""Set selected todo"""
		self.selected_todo = todo

	def get_todo(self) -> tuple[str | None, bool]:
		"""Get selected todo and do_something"""
		if self.destination_todos and self.selected_todo in self.destination_todos.keys():
			return self.selected_todo, self.destination_todos[self.selected_todo]["do_something"]
		else:
			return None, False

	def save(self, gui_geometry: str | None = None) -> None:
		"""Save settings file"""
		self.local_path.mkdir(parents=True, exist_ok=True)
		with self._path.open("w", encoding="utf-8") as fp:
			dump(
				{
					"destination": self.destination_name,
					"username": self.username,
					"sendmail": self.sendmail,
					"mail_to": self.mail_to,
					"mail_subject": self.mail_subject,
					"gui_geometry": gui_geometry or self.gui_geometry
				}, fp, indent=2
			)
