#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from time import perf_counter, strftime
from datetime import timedelta
from classes.logger import Logger as Log
from classes.destination import Destination
from classes.copymd5 import CopyMD5
from classes.size import Size
from classes.gimmicks import Rotator
from classes.sendmail import SendMail
if TYPE_CHECKING:
	from classes.source import Source
	from classes.settings import Settings
	from classes.path import Path
	from threading import Event
	from collections.abc import Callable

class Worker:
	"""Main functionality of Cirdan"""

	def __init__(
		self,
		source: Source,
		settings: Settings,
		kill: Event | None = None,
		echo: Callable[..., None] = print,
	) -> None:
		self._source = source
		self._settings = settings
		self._kill_switch = kill
		self._echo = echo
		self._destination = Destination(settings)
		self._target_dir_path = self._destination.path / self._source.name
		self._tsv_path = self._destination.path.joinpath(self._source.name, strftime(self._settings.tsv_name))
		self._mail_address = f"{self._settings.mail_to}@{self._settings.domain}" if self._settings.mail_to else None
		self._processed_bytes = Size(0)
		self._processed_files = 0
		self._read_errors = 0
		self._write_errors = 0
		self._mismatches = 0
		self._exceptions = 0
		self._indicator = Rotator()

	def _killed(self) -> bool:
		"""True when the kill switch has been set"""
		return bool(self._kill_switch and self._kill_switch.is_set())

	def _copy_error(self, copymd5: CopyMD5) -> str:
		"""Handle error from copy process"""
		stderr = copymd5.read_stderr().strip()
		try:
			read_errors, write_errors, mismatches = (int(p.split("(")[0]) for p in stderr.split(":")[1].split("/")[:3])
			error_msg = Log.error(message=self._settings.labels.copy_error.replace(
				"#1", f"{copymd5}").replace(
				"#2", read_errors).replace(
				"#3", write_errors).replace(
				"#4", mismatches)
			)
			self._read_errors += read_errors
			self._write_errors += write_errors
			self._mismatches += mismatches
		except ValueError, IndexError:
			error_msg = stderr
		Log.error(error_msg)

	def _update_progress(self, line: str, old_processed_files: int) -> None:
		"""Update progress"""
		if not (stripped := line.strip()):
			try:
				splitted = stripped.split()
				processed_files = int(splitted[1])
				if processed_files > old_processed_files:
					self._processed_bytes += Size(splitted[0])
					self._processed_files += processed_files
			except ValueError, IndexError:
				pass
		return self._settings.labels.copy_progress.replace(
			"#1", f"{self._processed_bytes}").replace(
			"#2", f"{self._source.size}").replace(
			"#3", f"{self._processed_files}").replace(
			"#4", f"{self._source.file_cnt}").replace(
			"#5", f"{self._source.size % self._processed_bytes}"
		) + f" {self._indicator.get()}"

	def _copy_directory(self, src_path: Path) -> bool:
		"""Copy one directory"""
		copymd5 = CopyMD5(src_path, self._target_dir_path, self._tsv_path)
		Log.info(self._settings.labels.running.replace("#", f"{copymd5}"))
		for line in copymd5.stdout:
			if self._killed():
				copymd5.terminate()
				return "killed"
			if not (stripped := line.strip()):
				continue
			self._echo(self._update_progress(stripped, self._processed_files), end="\r")
		if copymd5.wait() != 0:
			self._copy_error(copymd5)

	def _copy_file(self, src_path: Path) -> bool:
		"""Copy one file"""
		copymd5 = CopyMD5(src_path, self._target_dir_path, self._tsv_path)
		Log.info(self._settings.labels.running.replace("#", f"{copymd5}"))
		if copymd5.wait() != 0:
			self._copy_error(copymd5)

	def run(self) -> str | int:
		"""Copy process; return error list, or None if killed"""
		start_time = perf_counter()
		self._target_dir_path.mkdir(exist_ok=True)
		self._tsv_path.write_text(f"{self._settings.tsv_header}\n", encoding="utf-8")
		for values in self._source.sub_dirs.values():
			if returncode := self._copy_directory(values.get("path")):
				return returncode
		for values in self._source.sub_files.values():
			if returncode := self._copy_file(values.get("path")):
				return returncode
		try:
			self._tsv_path.copy_into(self._settings.log_path / self._destination.path.name / self._source.name)
		except:
			Log.error()
			self._exceptions += 1
		if self._settings.selected_todo:
			todo = self._destination.todos[self._settings.selected_todo]
		else:
			for todo, values in self._destination.todos.items():	# search for do_something == False
				if values["do_something"] == False:
					break
		try:
			self._destination.delete_trigger(todo, self._source)
		except:
			Log.warning()
			self._exceptions += 1
		try:
			self._destination.write_meta(todo, self._source)
		except:
			Log.error()
			self._exceptions += 1
		try:
			self._destination.write_trigger(todo, self._source)
		except:
			Log.error()
			self._exceptions += 1
		duration = timedelta(seconds=perf_counter() - start_time)
		if self._settings.sendmail and self._mail_address:
			try:
				SendMail(self._settings.mail).send(
					self._mail_address,
					self._settings.mail_subject,
					(
						f"{self._source.name}",
						f"{self._processed_bytes}",
						f"{self._processed_files}",
						f"{self._read_errors}",
						f"{self._write_errors}",
						f"{self._mismatches}"
					),
				)
			except Exception:
				Log.error(self._labels.mail_error.replace("#", f"{self._mail_address}"))
				self._exceptions += 1
		log_msg = self._settings.labels.copy_finished.replace(
			"#1", f"{self._processed_bytes}").replace(
			"#2", f"{self._processed_files}").replace(
			"#3", f"{self._read_errors}").replace(
			"#4", f"{self._write_errors}").replace(
			"#5", f"{self._mismatches}").replace(
			"#6", f"{self._exceptions}").replace(
			"#7", f"{duration}"
		)
		if self.errors:
			Log.error(log_msg)
		else:
			Log.info(log_msg)
		return self._write_errors + self._read_errors + self._mismatches + self._exceptions