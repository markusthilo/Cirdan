#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Callable
from threading import Event
from classes.logger import Logger as Log
from classes.path import Path
from classes.copymd5 import CopyMD5
from classes.size import Size
from classes.gimmicks import Rotator
from classes.regex import RegEx
from classes.sendmail import SendMail
from classes.source import Source
from classes.settings import Settings

class Worker:
	"""Main functionality of Cirdan"""

	def __init__(
		self,
		source: Source,
		settings: Settings,
		logger: Log,
		user_log: Path | None = None,
		kill: Event | None = None,
		echo: Callable[..., None] = print,
	) -> None:
		self._source = source
		self._settings = settings
		self._logger = logger
		self._user_log = user_log
		if user_log:
			self._logger.add_user(user_log)
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f"{self._settings.mail_to}@{self._settings.domain}" if self._settings.mail_to else None
		self._destination_path = self._settings.destination_path / source.name

		self._tsv_path = None
		self._processed_bytes = Size(0)
		self._processed_files = 0
		self._read_errors = 0
		self._write_errors = 0
		self._mismatches = 0
		self._indicator = Rotator()

	def _killed(self) -> bool:
		"""True when the kill switch has been set"""
		return bool(self._kill_switch and self._kill_switch.is_set())

	def _error(self, copymd5: CopyMD5) -> str:
		"""Handle error"""
		stderr = copymd5.read_stderr().strip()
		try:
			read_errors, write_errors, mismatches = (int(p.split("(")[0]) for p in stderr.split(":")[1].split("/")[:3])
			msg = Log.error(message=self._settings.labels.copy_error.replace(
				"#1", f"{copymd5}").replace(
				"#2", read_errors).replace(
				"#3", write_errors).replace(
				"#4", mismatches
			)
			self._read_errors += read_errors
			self._write_errors += write_errors
			self._mismatches += mismatches
		except ValueError, IndexError:
			msg = stderr
		Log.error(msg)
		return msg

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

	def _copy_file(self, src_path: Path) -> bool:
		"""Copy one file"""
		copymd5 = CopyMD5(src_path, self._destination_path, self._tsv_path)
		Log.info(self._settings.labels.running.replace("#", f"{copymd5}"))
		if copymd5.wait() != 0:
			self.echo(self._error(copymd5))

	def _copy_directory(self, src_path: Path) -> bool:
		"""Copy one directory"""
		copymd5 = CopyMD5(src_path, self._destination_path, self._tsv_path)
		Log.info(self._settings.labels.running.replace("#", f"{copymd5}"))
		for line in copymd5.stdout:
			if self._killed():
				copymd5.terminate()
				return None
			if not (stripped := line.strip()):
				continue
			self._echo(self._update_progress(stripped, self._processed_files), end="\r")
		if copymd5.wait() != 0:
			self.echo(self._error(copymd5))
		



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
				self._labels.size_mismatch
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
			self.self._source.name
		try:
			self._tsv_path = self._destination_path.write_text_file(
				self._settings.tsv_name,
				self._settings.tsv_header,
				use_strftime=True,
			)
		except OSError:
			return self._error(self._settings.labels.bad_destination.replace("#", f"{self._destination_path}"))
		try:


		 in self._sources:
				result = self._copy_source(source, destination_root_path)
				if result is None:
					return None
			return self.errors

		try:
			self._logger.close_user()
		except Exception:
			Log.warning()
