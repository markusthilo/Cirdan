#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Callable
from threading import Event
from classes.logger import Logger as Log
from classes.path import Path
from classes.copymd5 import CopyMD5
from classes.size import Size
from classes.gimmicks import IndicatorThread
from classes.regex import RegEx
from classes.sendmail import SendMail
from classes.source import Source
from classes.settings import Settings

class Worker:
	"""Main functionality of Cirdan"""

	def __init__(
		self,
		sources: list[Source],
		settings: Settings,
		logger: Log,
		user_log: Path | None = None,
		kill: Event | None = None,
		echo: Callable[..., None] = print,
	) -> None:
		self._sources = sources
		self._settings = settings
		self._labels = settings.labels
		self._destination = settings.destination
		self._logger = logger
		self._user_log = user_log
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = (
			f"{self._settings.mail_to}@{self._settings.domain}"
			if self._settings.mail_to else None
		)
		self.errors: list[str] = []

	def _killed(self) -> bool:
		"""True when the kill switch has been set"""
		return bool(self._kill_switch and self._kill_switch.is_set())

	def _error(self, message: str | None = None) -> None:
		"""Handle error"""
		msg = Log.error(message=message)
		self._echo(msg)
		self.errors.append(msg)

	def _check_sources(self, destination_root_path: Path) -> list[str] | None:
		"""Validate sources (and existing destination trees); None means killed"""
		for source in self._sources:
			Log.info(self._labels.checking_source.replace("#", f"{source}"))
			for path, bad in source.check(kill=self._kill_switch):
				if self._killed():
					return None
				self._echo(f"{path}", end="\r")
				if isinstance(bad, int):
					self._echo()
					self._error(
						self._labels.path_too_long
						.replace("#1", f"{path}")
						.replace("#2", f"{bad}")
						.replace("#3", f"{self._settings.max_path_length}")
					)
					return self.errors
				if isinstance(bad, str):
					self._echo()
					self._error(
						self._labels.blacklisted
						.replace("#1", f"{path}")
						.replace("#2", f"{bad}")
					)
					return self.errors
			if self._killed():
				return None
			if source.whitelist and not source.whitelist_match:
				self._echo()
				self._error(self._labels.no_whitelist_match.replace("#", f"{source.path}"))
				return self.errors
			Log.info(
				self._labels.found_files_in_source
				.replace("#1", f"{source.files}")
				.replace("#2", f"{source.path}")
				.replace("#3", f"{source.size}")
			)
			if self._settings.destination_blacklist:
				destination_path = destination_root_path / source.name
				if destination_path.is_dir():
					Log.info(self._labels.checking_destination.replace("#", f"{destination_path}"))
					blacklist = RegEx(self._settings.destination_blacklist)
					for path, relative in destination_path.rrglob("*"):
						if self._killed():
							return None
						if pattern := blacklist.search(relative):
							self._error(
								self._labels.destination_blocked_by
								.replace("#1", path.name)
								.replace("#2", f"{pattern}")
							)
							self._echo()
							return self.errors
		return self.errors if self.errors else []

	def _copy_source(self, source: Source, destination_root_path: Path) -> bool | None:
		"""
		Copy one source. Returns True on success, False on failure, None if killed.
		"""
		destination_path = destination_root_path / source.name
		processed_files = 0
		read_errors = 0
		write_errors = 0
		mismatches = 0
		total_files: int | None = None
		total_bytes: Size | None = None
		total_time = ""
		tsv = f"{self._labels.tsv_header}\n"

		if error := self._logger.add_remote(source.path, destination_path):
			self._error(error)

		todo = self._settings.selected_todo
		if todo:
			self._destination.delete_trigger(todo, destination_path)

		Log.info(self._labels.copying.replace("#", f"{source.name}"))
		indicator = IndicatorThread(
			message=f"% {self._labels.of} {source.name} #",
			echo=self._echo,
		)
		indicator.start()
		try:
			copymd5 = CopyMD5(source.path, destination_root_path)
			for line in copymd5.stdout:
				if self._killed():
					copymd5.terminate()
					return None
				if not (stripped := line.strip()):
					continue
				if stripped.startswith('"'):
					tsv += line if line.endswith("\n") else f"{line}\n"
					splitted = stripped.split("\t")
					if len(splitted) < 4:
						continue
					status = splitted[-1]
					mid = splitted[-2]
					if status == "OK":
						processed_files += 1
						size: Size | str = Size(mid)
					elif mid == "ERROR":
						mismatches += 1
						size = "-"
					elif mid == "FAILED":
						read_errors += 1
						size = "-"
					else:
						write_errors += 1
						try:
							size = Size(mid)
						except (TypeError, ValueError):
							size = mid
					self._echo(
						" ".join(splitted[:-3]).strip('"') + f"    {size}    {status}"
					)
					continue
				if stripped.startswith("...processed"):
					parts = stripped.split()
					if len(parts) >= 2:
						processed_bytes = Size(parts[1])
						indicator.set_percentage(processed_bytes % source.size)
					continue
				if stripped.startswith("...finished"):
					parts = stripped.split()
					# ...finished, processed N file(s), N bytes, took TIME
					try:
						total_files = int(parts[2])
						total_bytes = Size(parts[4])
						total_time = parts[7] if len(parts) > 7 else ""
					except (IndexError, ValueError):
						Log.warning(f"Could not parse finished line: {stripped}")
						continue
					indicator.set_percentage(100)
					Log.info(
						self._labels.copy_finished
						.replace("#1", f"{total_files}")
						.replace("#2", f"{total_bytes}")
						.replace("#3", f"{total_time}")
					)
			returncode = copymd5.wait()
		finally:
			indicator.kill()
			indicator.join(timeout=1)

		ok = returncode == 0
		if returncode != 0:
			self._error(f"{copymd5} returned {returncode}: {copymd5.read_stderr()}")
		if read_errors:
			self._error(self._labels.read_error.replace("#", f"{read_errors}"))
			ok = False
		if write_errors:
			self._error(self._labels.write_error.replace("#", f"{write_errors}"))
			ok = False
		if mismatches:
			self._error(self._labels.mismatch.replace("#", f"{mismatches}"))
			ok = False
		if total_files is not None and total_files != source.files:
			self._error(
				self._labels.file_count_mismatch
				.replace("#1", f"{source.files}")
				.replace("#2", f"{total_files}")
			)
			ok = False
		if total_bytes is not None and total_bytes != source.size:
			self._error(
				self._labels.size_missmatch
				.replace("#1", f"{source.size}")
				.replace("#2", f"{total_bytes}")
			)
			ok = False

		Log.debug("Writing TSV files")
		try:
			destination_path.mkdir(parents=True, exist_ok=True)
			destination_path.write_text_file(self._settings.tsv_name, tsv, use_strftime=True)
			if remote_parent := self._logger.get_remote_parent():
				remote_parent.write_text_file(self._settings.tsv_name, tsv, use_strftime=True)
		except OSError:
			self._error()

		if ok and todo:
			try:
				self._destination.write_meta(
					todo, destination_path, source.counted_paths or {}
				)
				self._destination.write_trigger(todo, destination_path)
			except Exception:
				self._error()

		if ok and self._settings.sendmail and self._mail_address:
			try:
				SendMail(self._settings.mail).send(
					self._mail_address,
					self._settings.mail_subject,
					(
						f"{source.name}",
						f"{total_bytes if total_bytes is not None else source.size}",
						f"{total_files if total_files is not None else processed_files}",
						f"{read_errors}",
						f"{write_errors}",
						f"{mismatches}",
					),
				)
			except Exception:
				self._error(self._labels.mail_error.replace("#", f"{self._mail_address}"))

		try:
			self._logger.close_remote()
		except Exception:
			Log.warning()

		return ok

	def run(self) -> list[str] | None:
		"""Copy process; return error list, or None if killed"""
		try:
			if not self._sources:
				self._error(self._labels.no_sources)
				return self.errors
			if not self._destination:
				self._error(self._labels.bad_destination.replace("#", ""))
				return self.errors
			destination_root_path = self._destination.path
			if not destination_root_path.is_accessible():
				self._error(
					self._labels.bad_destination.replace("#", f"{destination_root_path}")
				)
				return self.errors
			if self._user_log:
				self._logger.add_user(self._user_log)

			checked = self._check_sources(destination_root_path)
			if checked is None:
				return None
			if self.errors:
				return self.errors

			for source in self._sources:
				result = self._copy_source(source, destination_root_path)
				if result is None:
					return None
			return self.errors
		finally:
			try:
				self._logger.close_user()
			except Exception:
				Log.warning()
