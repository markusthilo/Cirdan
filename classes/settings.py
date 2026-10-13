#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import executable as __executable__
from platform import node, system
from json import load, dump
from getpass import getuser
from pprint import pformat
from types import SimpleNamespace
from classes.path import Path
from classes.destination import Destination

__app_path__ = Path(__file__).parent.parent if Path(__executable__).name.startswith('python') else Path(__executable__).parent

class Settings:
	"""User settings, configuration and labels"""

	def __init__(self,
		version: str = "2_Under_Construction",
		config: Path | None = None,
		destination: str | None = None,
		destination_path: Path | str | None = None,
		username: str | None = None,
		mail_to: str | None = None,
		mail_subject: str | None = None
	) -> None:
		if destination_path is not None and not destination:
			raise ValueError("Destination path provided without destination name")
		self.version = version
		self.app_path = __app_path__
		self.system = system()
		self.hostname = node()
		config_path = Path(config).resolve() if config else self.app_path.joinpath("config.json")
		with config_path.open(encoding="utf-8") as fp:
			for key, value in load(fp).items():
				if key == "paths":
					for path_key, path_value in value[self.system].items():
						self.__dict__[path_key] = self._resolve_path(path_value)
				else:	
					self.__dict__[key] = value
		with self.labels_path.open(encoding="utf-8") as fp:
			self.labels = SimpleNamespace(**load(fp))
		self._path = self.local_path / self.settings_name
		self.accessible_destinations = dict[str, Destination]()
		for dst_name in self.destinations:
			dst = Destination(self, dst_name)
			if dst.is_accessible():
				self.accessible_destinations[dst_name] = dst
		if destination and destination_path:
			self.destination = Destination(self, destination, destination_path)
		elif destination:
			self.destination = self.accessible_destinations[destination] if destination in self.accessible_destinations else None
		elif len(self.accessible_destinations) == 1:
			self.destination = next(iter(self.accessible_destinations))
		else:
			self.destination = None
		if not self.destination:
			self.destination_path = None
		try:
			with self._path.open(encoding="utf-8") as fp:
				items = load(fp)
		except FileNotFoundError:
			items = {}
			try:
				self.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		self.username = username if username else items["username"] if "usernmae" in items and items["username"] else getuser()
		self.sendmail = True if mail_to else bool(items["sendmail"]) if "sendmail" in items else False
		self.mail_to = mail_to if mail_to else items["mail_to"] if "mail_to" in items else ""
		self.mail_subject = mail_subject if mail_subject else items["mail_subject"] if "mail_subject" in items else self.mail["default-subject"]
		self.selected_todo = None
		self.id = f'{{\n  "hostname": "{self.hostname}",\n  "username": "{self.username}"\n}}'

	def __repr__(self) -> str:
		"""Readable key/value listing of the user settings"""
		lines = ["Settings:"]
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

	def _resolve_path(self, path_value: str) -> Path:
		"""Expand $HOME / $APP prefixes (case-insensitive) and resolve"""
		normalized = path_value.replace("\\", "/")
		upper = normalized.upper()
		if upper.startswith("$HOME/"):
			return Path().home().joinpath(normalized[6:]).resolve()
		if upper.startswith("$APP/"):
			return self.app_path.joinpath(normalized[5:]).resolve()
		return Path(path_value).resolve()

	def set_destination(self, destination: str) -> None:
		"""Set selected destination"""
		self.destination = self.accessible_destinations[destination] if destination in self.accessible_destinations else None

	def set_todo(self, todo: str) -> None:
		"""Set selected todo"""
		self.selected_todo = todo

	def save(self) -> None:
		"""Save settings file"""
		self.local_path.mkdir(parents=True, exist_ok=True)
		data = {
			"destination": self.destination,
			"destination_path": str(self.destination_path) if self.destination_path else None,
			"username": self.username,
			"sendmail": self.sendmail,
			"mail_to": self.mail_to,
			"mail_subject": self.mail_subject,
		}
		with self._path.open("w", encoding="utf-8") as fp:
			dump(data, fp, indent=2)
