#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from sys import exc_info
from traceback import format_exc
from collections.abc import Callable
from classes.path import Path
from classes.settings import Settings
from classes.labels import Labels

class Logger:
	"""Configure Logging"""

	@staticmethod
	def debug(message: str) -> None:
		"""Log debug message"""
		logging.debug(message)

	@staticmethod
	def info(message: str) -> None:
		"""Log info message"""
		logging.info(message)

	@staticmethod
	def exception(level: str, message: str | None = None) -> str:
		"""Log exception; include active traceback when present"""
		parts: list[str] = []
		if message:
			parts.append(f"{message}")
		ex_type, ex_text, traceback = exc_info()
		if ex_type:
			parts.append(f"{ex_type.__name__}: {ex_text}")
		if traceback:
			parts.append(format_exc().strip())
		msg = ", ".join(parts) if parts else "Unknown error"
		logging.__dict__[level.lower()](msg)
		return msg

	@staticmethod
	def warning(message: str | None = None) -> str:
		"""Log warning"""
		return Logger.exception("warning", message=message)

	@staticmethod
	def error(message: str | None = None) -> str:
		"""Log error"""
		return Logger.exception("error", message=message)

	@staticmethod
	def critical(message: str | None = None) -> str:
		"""Log critical error"""
		return Logger.exception("critical", message=message)

	def __init__(self, settings: Settings, labels: Labels, echo: Callable[..., None] = print) -> None:
		self._settings = settings
		self._config = settings.config
		self._settings = settings
		self._labels = labels
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		self._echo_handler: logging.Handler | None = None
		self._echo_handler = self.set_echo(echo=echo)
		self._config.local_path.mkdir(parents=True, exist_ok=True)
		self._lastlog_path = self._config.local_path.joinpath(self._config.lastlog_name)
		self._lastlog_handler = self.add_file(self._lastlog_path)
		self._remote_path: Path | None = None
		self._remote_handler: logging.Handler | None = None
		self._user_path: Path | None = None
		self._user_handler: logging.Handler | None = None
		self._user_messages: list[str] = []
		self.basic_info = f"{self._labels.hostname}: {self._settings.hostname}, {self._labels.username}: {self._settings.username}, {self._labels.title} v{self._labels.version}"
		self.debug(f"{self.basic_info} {self._labels.launched}")

	def add_file(self, path: Path, level: int = logging.DEBUG) -> logging.Handler:
		"""Add log file"""
		handler = logging.FileHandler(mode="w", filename=path)
		handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
		handler.setLevel(level)
		self._logger.addHandler(handler)
		return handler

	def set_echo(self, echo: Callable[..., None] = print) -> logging.Handler:
		"""Set how to echo messages"""
		level = logging.INFO
		class echo_stream:
			def write(self, msg: str) -> int:
				text = msg.strip()
				if text:
					echo(text)
				return len(msg)

			def flush(self) -> None:
				pass

		if self._echo_handler:
			level = self._echo_handler.level
			self._logger.removeHandler(self._echo_handler)
			self._echo_handler.close()
		self._echo_handler = logging.StreamHandler(stream=echo_stream())
		self._echo_handler.setLevel(level)
		self._logger.addHandler(self._echo_handler)
		return self._echo_handler

	def add_user(self, path: Path, level: int = logging.INFO) -> None:
		"""Add user log, logs to RAM / variable until closing"""
		self.debug(f"Setting up user log, path: {path}")
		self._user_path = path.resolve()
		self._user_messages = []
		logger = self
		class store_stream:
			def write(self, msg: str) -> int:
				text = msg.strip()
				if text:
					logger._user_messages.append(text)
				return len(msg)
			def flush(self) -> None:
				pass
		self._user_handler = logging.StreamHandler(stream=store_stream())
		self._user_handler.setLevel(level)
		self._logger.addHandler(self._user_handler)
		self.info(f"{self.basic_info}, {self._labels.logfile}")

	def close_user(self) -> None:
		"""Close user log"""
		if not self._user_handler:
			return
		self._logger.removeHandler(self._user_handler)
		self._user_handler.close()
		self._user_handler = None
		self.debug("Closing user log")
		if self._user_path:
			self._user_path.write_text("\n".join(self._user_messages), encoding="utf-8")
		self._user_messages = []

	def add_remote(self, source: Path, destination: Path) -> str | None:
		"""Add remote log file; return error message on failure"""
		msg = f"{self.basic_info}, {self._labels.source_dir}: {source}, {self._labels.destination}: {destination}"
		self._remote_path = self._config.log_path.joinpath(source.name, self._config.log_name).timed()
		try:
			self._remote_path.parent.mkdir(parents=True, exist_ok=True)
			self._remote_handler = self.add_file(self._remote_path)
			self.debug(msg)
			return None
		except Exception:
			if self._remote_handler:
				try:
					self._logger.removeHandler(self._remote_handler)
					self._remote_handler.close()
				except Exception:
					pass
				self._remote_handler = None
			self.error()
			self._remote_path = self._config.log_path.joinpath(f"{source.name}_{self._config.log_name}").timed()
			try:
				self._remote_path.parent.mkdir(parents=True, exist_ok=True)
				self._remote_handler = self.add_file(self._remote_path)
				self.debug(msg)
				return None
			except Exception:
				self._remote_path = None
				self._remote_handler = None
				return self.error()

	def get_remote_parent(self) -> Path | None:
		"""Get parent of remote log file"""
		if self._remote_path:
			return self._remote_path.parent
		return None

	def close_remote(self) -> None:
		"""Close remote log file"""
		self.debug(f"Closing remote log, path: {self._remote_path}")
		if self._remote_handler:
			self._logger.removeHandler(self._remote_handler)
			self._remote_handler.close()
			self._remote_handler = None
		self._remote_path = None

	def crash(self, message: str | None = None) -> str:
		"""Close all logs on crash and try to copy crashlog"""
		message = self.critical(message=message)
		self.close_remote()
		self.close_user()
		self._logger.removeHandler(self._lastlog_handler)
		self._lastlog_handler.close()
		logging.shutdown()
		try:
			self._lastlog_path.copy(self._config.log_path.joinpath(
				f"{self._settings.username}_{self._config.crashlog_name}").timed())
		except Exception:
			pass
		return message
