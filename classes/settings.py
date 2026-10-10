#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load, dump
from getpass import getuser
from pprint import pformat
from classes.path import Path
from classes.config import Config

class Settings:
	"""User settings to save locally per user"""

	KEYS = ("destination", "destination_path", "username", "sendmail", "mail_to", "mail_subject")

	def __init__(self, config: Config,
		destination: str | None = None,
		username: str | None = None,
		mail_to: str | None = None,
		mail_subject: str | None = None,
		sendmail: bool | None = None,
		*,
		destination_path: Path | str | None = None
	) -> None:
		if destination_path is not None and not destination:
			raise ValueError("Destination path provided without destination name")
		self._config = config
		self._path = config.local_path / config.settings_name
		self._destination_path_override: Path | None = (
			Path(destination_path).resolve() if destination_path is not None else None
		)
		items = self._load_items()
		self.destination = destination or self._get_str(items, "destination")
		if self._destination_path_override is None:
			if saved := self._get_str(items, "destination_path"):
				# keep a saved override only when destination has no config mapping
				if not self._path_key_for(self.destination):
					self._destination_path_override = Path(saved)
		self.username = username or self._get_str(items, "username") or getuser()
		self.sendmail = sendmail if sendmail is not None else self._get_bool(items, "sendmail")
		self.mail_to = mail_to or self._get_str(items, "mail_to")
		self.mail_subject = (
			mail_subject
			or self._get_str(items, "mail_subject")
			or config.mail["default-subject"]
		)

	def _load_items(self) -> dict[str, object]:
		try:
			with self._path.open(encoding="utf-8") as fp:
				loaded = load(fp)
			if isinstance(loaded, dict):
				return {str(key): value for key, value in loaded.items() if value is not None}
		except FileNotFoundError:
			try:
				self._config.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		except Exception:
			try:
				self._config.local_path.mkdir(parents=True, exist_ok=True)
			except OSError:
				pass
		return {}

	def _path_key_for(self, destination: str | None) -> str | None:
		if not destination:
			return None
		return self._config.destinations.get(destination, {}).get("path")

	@property
	def destination_path(self) -> Path | None:
		"""Resolved destination directory; follows destination unless overridden"""
		if self._destination_path_override is not None:
			return self._destination_path_override
		path_key = self._path_key_for(self.destination)
		if not path_key:
			return None
		return Path(self._config.__dict__[path_key])

	@destination_path.setter
	def destination_path(self, value: Path | str | None) -> None:
		self._destination_path_override = Path(value).resolve() if value is not None else None

	@staticmethod
	def _get_str(items: dict[str, object], key: str) -> str | None:
		value = items.get(key)
		if value is None or value == "":
			return None
		return str(value)

	@staticmethod
	def _get_bool(items: dict[str, object], key: str, default: bool = False) -> bool:
		value = items.get(key, default)
		if isinstance(value, str):
			return value.strip().lower() in ("1", "true", "yes", "on")
		return bool(value)

	def __repr__(self) -> str:
		"""Readable key/value listing of the user settings"""
		items = {key: getattr(self, key) for key in self.KEYS}
		lines = ["Settings:"]
		width = max((len(key) for key in items), default=0)
		for key, value in items.items():
			formatted = pformat(value, width=76, sort_dicts=False)
			if "\n" in formatted:
				indented = formatted.replace("\n", "\n" + " " * (width + 3))
				lines.append(f"  {key:<{width}} = {indented}")
			else:
				lines.append(f"  {key:<{width}} = {formatted}")
		return "\n".join(lines)

	def save(self) -> None:
		"""Save settings file"""
		self._config.local_path.mkdir(parents=True, exist_ok=True)
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
