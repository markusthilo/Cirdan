#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from platform import node
from json import load, dump
from getpass import getuser
from pprint import pformat
from classes.path import Path
from classes.destination import Destination

if TYPE_CHECKING:
	from classes.config import Config

class Settings:
	"""User settings to save locally per user"""

	KEYS = ("destination", "destination_path", "username", "sendmail", "mail_to", "mail_subject")

	def __init__(self, config: Config,
		destination: str | None = None,
		destination_path: Path | str | None = None,
		username: str | None = None,
		mail_to: str | None = None,
		mail_subject: str | None = None
	) -> None:
		if destination_path is not None and not destination:
			raise ValueError("Destination path provided without destination name")
		self.config = config
		self._path = self.config.local_path / self.config.settings_name
		items = self._load_items()
		if destination and destination_path:
			self.destination = Destination(self, destination, destination_path)
		elif destination:
			self.destination = self.config.accessible_destinations[destination] if destination in self.config.accessible_destinations else None
		else:
			self.destination = None
		if not self.destination:
			self.destination_path = None
		self.username = username if username else items["username"] if "usernmae" in items and items["username"] else getuser()
		self.sendmail = True if mail_to else bool(items["sendmail"]) if "sendmail" in items else False
		self.mail_to = mail_to if mail_to else items["mail_to"] if "mail_to" in items else ""
		self.mail_subject = mail_subject if mail_subject else items["mail_subject"] if "mail_subject" in items else config.mail["default-subject"]
		self.hostname = node()
		self.id = f'{{"hostname": {self.hostname}, "username": {self.username}}}'

	def __repr__(self) -> str:
		"""Readable key/value listing of the user settings"""
		lines = ["Settings:"]
		width = max((len(key) for key in self.KEYS), default=0)
		for key in self.KEYS:
			value = self.__dict__[key] if key in self.__dict__ else None
			formatted = pformat(value, width=76, sort_dicts=False)
			if "\n" in formatted:
				indented = formatted.replace("\n", "\n" + " " * (width + 3))
				lines.append(f"  {key:<{width}} = {indented}")
			else:
				lines.append(f"  {key:<{width}} = {formatted}")
		return "\n".join(lines)

	def _load_items(self) -> dict[str, object]:
		try:
			with self._path.open(encoding="utf-8") as fp:
				loaded = load(fp)
			if isinstance(loaded, dict):
				return {str(key): value for key, value in loaded.items() if value is not None}
		except FileNotFoundError:
			try:
				self.config.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		except Exception:
			try:
				self.config.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		return {}

	def save(self) -> None:
		"""Save settings file"""
		self.config.local_path.mkdir(parents=True, exist_ok=True)
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
