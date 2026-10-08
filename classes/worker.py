#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.logger import Logger as Log
from classes.path import Path
from classes.copymd5 import CopyMD5
from classes.size import Size
from classes.gimmicks import IndicatorThread
from classes.regex import RegEx
from classes.sendmail import SendMail 

class Worker:
	"""Main functionality of Cirdan"""

	def __init__(self,
		sources: list[Path],
		todo: Todo,
		config: Config,
		labels: Labels,
		settings: Settings,
		logger: Logger,
		user_log: Path | None = None,
		kill: threading.Event | None = None,
		echo: Callable[[str], None] = print
	):
		self._sources = sources
		self._todo = todo
		self._config = config
		self._labels = labels
		self._settings = settings
		self._logger = logger
		self._user_log = user_log
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.mail_to}@{self._config.domain}' if self._settings.mail_to else None
		self.errors = list[str]()

	def _error(self, message: str | None = None) -> None:
		"""Handle error"""
		self.errors.append(Log.error(message=message))

	def run(self) -> list[str]:
		"""Copy process"""
		if not self._sources:
			self._error(self._labels.no_sources)
			return self.errors
		try:
			destination_root_path = self._config.target_path.joinpath(
				self._config.destinations[self._settings.destination]["sub_path"]
				)
		except:
			self._error(self._labels.bad_destination.replace("#", f"{self._settings.destination}"))
			return self.errors
		if not destination_root_path.is_accessable_dir():
			self._error(self._labels.bad_destination.replace("#", f"{destination_root_path}"))
			return self.errors
		if self._user_log:	# start additional log if selected
			self._logger.add_user(self._user_log)
		for source in self._sources:	# check destination and create subdirs if necessary
			Log.info(self._labels.checking_source.replace("#", f"{source}"))
			for path, bad in source.check():
				if self._kill_switch and self._kill_switch.is_set():
					return
				self._echo(f"{path}", end="\r")
				if isinstance(bad, int):
					self._echo()
					self._error(self._labels.path_too_long.replace(
					"#1", f"{path}").replace(
					"#2", f"{bad}").replace(
					"#3", f"{self._config.max_path_length}")
				)
					return self.errors
				if isinstance(bad, str):
					self._echo()
					self._error(self._labels.blacklisted.replace("#1", f"{path}").replace("#2", f"{bad}"))
					return self.errors
			if source.whitelist and not source.whitelist_match:
				self._echo()
				self._error(self._labels.no_whitelist_match.replace("#", f"{source.path}"))
				return self.errors
			Log.info(self._labels.found_files_in_source.replace(
				"#1", f"{len(source.files)}").replace(
				"#2", f"{source.path}").replace(
				"#3", f"{source.size}")
			)
			destination_path = destination_root_path / source.name
			if self._config.destination_blacklist and destination_path.is_dir():	# check for blacklisted files in destination
				Log.info(self._labels.checking_destination.replace("#", f'{destination_path}'))
				blacklist = RegEx(self._config.destination_blacklist)
				for path in destination_path.rrglob("*"):
					if self._kill_switch and self._kill_switch.is_set():
						return
					if pattern := blacklist.search(path.name):
						self._error(self._labels.destination_blocked_by.replace("#1", path.name).replace("#2", f'{pattern}'))
						self._echo()
						return self.errors
		for source in self._sources:	# copy sources one by one
			destination_path = destination_root_path / source.name
			processed_files = 0
			read_errors = 0
			write_errors = 0
			mismatches = 0
			tsv = f"{self._labels.tsv_header}\n"
			if error := self._logger.add_remote(source.path, destination_path):	# add log for one source / one destination
				self._error(error)
			self._todo.delete_trigger(destination_path)
			Log.info(f"{self._labels.starting}: {copymd5}")
			indicator = IndicatorThread(message=f"% {self._labels.of} {source.name} #", echo=self._echo)
			copymd5 = CopyMD5(source.path, destination_path)
			for line in copymd5.stdout:
				if stripped := line.strip():
					if stripped.startswith('"'):
						tsv += line
						splitted = stripped.split("\t")
						if splitted[-1] == "OK":
							processed_files += 1
							size = Size(splitted[-2])
						elif splitted[-2] == "ERROR":
							mismatches += 1
							size = '-'
						elif splitted[-2] == "FAILED":
							read_errors += 1
							size = '-'
						else:
							write_errors += 1
							size = Size(splitted[-2])
						self._echo(" ".join(splitted[:-3]).strip('"') + f"{size}\t{splitted[-1]}")
						continue
					if stripped.startswith("...processed"):
						processed_bytes = Size(stripped.split()[1])
						indicator.set_percentage(processed_bytes % source.size)
						continue
					if stripped.startswith("...finished"):
						total_bytes = Size(stripped.split()[1])
						indicator.set_percentage(100)
						Log.info(self._labels.copy_finished.replace("#", f'{total_bytes}'))
						break
					if self._kill_switch and self._kill_switch.is_set():
						copymd5.terminate()
						indicator.kill()
						return
			if read_errors:
				self._error(self._labels.read_error.replace("#", f"{read_errors}"))
			if write_errors:
				self._error(self._labels.write_error.replace("#", f"{write_errors}"))
			if mismatches:
				self._error(self._labels.mismatch.replace("#", f"{mismatches}"))
			if total_bytes != source.size:
				self._error(self._labels.size_missmatch.replace("#1", f"{total_bytes}").replace("#2", f"{source.size}"))
			Log.debug(f"Writing TSV files")
			destination_path.write_text_file(self._config.tsv_name, tsv, use_strftime=True)
			self._logger.get_remote_parent().write_text_file(self._config.tsv_name, tsv, use_strftime=True)
			self._todo.write_meta(destination_path, processed_files)
			self._todo.write_trigger(destination_path, self._logger.id)
			if self._settings.sendmail and self._mail_address:	# send mail to user
				try:
					SendMail(self._config.mail).send(
						self._mail_address,
						self._settings.mail_subject,
						(f"{source.name}", f"{source.size}", f"{len(source.files)}", f"{read_errors}", f"{write_errors}", f"{mismatches}")
					)
				except:
					self._error(self._labels.mail_error.replace("#", f"{self._mail_address}"))
			try:
				self._logger.close_remote()
			except:
				Log.warning()
		try:
			self._logger.close_user()
		except:
			Log.warning()
		return self.errors
