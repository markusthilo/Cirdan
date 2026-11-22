#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from copy import copy
from tkinter.messagebox import askyesno
from classes.worker import Worker
from classes.logger import Logger as Log
from classes.source import Source
from classes.gimmicks import Cylon
if TYPE_CHECKING:
	from classes.gui import Gui
	from classes.path import Path
	from typing import Callable

class InsertSrcDirThread(Thread):
	"""Thread to add a sub directory into source"""

	def __init__(self, gui: Gui, arg: Path | str, call_on_finish: Callable | None = None) -> None:
		self._gui = gui
		self._call_on_finish = call_on_finish
		self._source = copy(self._gui.source) if self._gui.source else Source(self._gui.settings)
		self._dir_path = self._source.top_dir(arg)
		if self._dir_path:
			self._insert = self._source.insert_top_dir
		else:
			self._dir_path = self._source.sub_dir(arg)
			if self._dir_path:
				if dir_name := self._source.sub_dir_already_set(self._sub_dir):
					raise ValueError(self._gui.labels.sub_dir_already_set.replace("#", dir_name)) from None
				self._insert = self._source.add_sub_dir
			else:
				raise ValueError(self._gui.labels.not_a_valid_directory.replace("#", str(arg))) from None
		self._indicator = Cylon()
		super().__init__(daemon=True)
		self._kill_event = Event()

	def _warning_yesno(self, message: str) -> bool:
		"""Show askyesno on the Tk main thread and wait for the answer"""
		result: list[bool] = []
		done = Event()
		def ask() -> None:
			try:
				self._gui.prepare_dialog()
				result.append(askyesno(parent=self._gui, title=self._labels.warning, message=message))
			except Exception:
				result.append(False)
			finally:
				done.set()
		try:
			self._gui.after(0, ask)
		except Exception:
			return False
		done.wait()
		return result[0] if result else False

	def run(self) -> None:
		"""Run thread to check and add source"""
		Log.debug(f"{self._gui.labels.checking} {self._dir_path}")
		for rel_path, error in self._insert(self._dir_path):
			if self._kill_event.is_set():
				return
			self._gui.echo(self._indicator.get(), end="\r")
			if error:
				if isinstance(error, int):
					if self._warning_yesno(
						f"{(self._gui.labels.path_to_long.replace(
								"#1", str(rel_path)).replace(
								"#2", str(error)).replace(
								"#3", str(self._gui.source.max_path_length))
						)} {error}\n\n{self._gui.labels.ignore_warning}"
					) and self._warning_yesno(self._labels.are_you_sure):
						self._gui.source.max_path_length = 0
						continue
				elif isinstance(error, str):
					if self._warning_yesno(
						f"{(self._gui.labels.blacklisted.replace(
								"#1", str(rel_path)).replace(
								"#2", str(error))
						)} {error}\n\n{self._gui.labels.ignore_warning}"
					) and self._warning_yesno(self._labels.are_you_sure):
						self._gui.source.blacklist = None
						continue
				self._gui.echo(self._gui.label.aborted_source_check)
				return
		self._gui.source = self._source
		self._gui.echo(self._gui.labels.added_source.replace("#", str(self._dir_path)))
		if self._call_on_finish:
			self._call_on_finish()

	def kill(self) -> None:
		"""Kill thread"""
		self._kill_event.set()

class InsertSourcesThread(InsertSrcDirThread):
	"""Thread to insert multiple sources"""

	def __init__(self, gui: Gui, sources: list[Path | str]) -> None:
		self._gui = gui
		self._sources = sources
		super().__init__(daemon=True)
		self._kill_event = Event()

	def run(self) -> None:
		"""Run thread to insert multiple sources"""
		for source in self._sources:
			if source.is_dir():
				try:
					self._gui.source_thread = InsertSrcDirThread(self._gui, source)
				except ValueError as ex:
					self._gui.echo(ex)
					continue
				self._gui.source_thread.start()
				self._gui.source_thread.join()
			elif source.is_file():
				self._gui.source.add_sub_file(source)
			else:
				Log.error(self._gui.labels.error_inserting_source.replace("#", str(source)))
		self._gui.gen_source_tree()
			
class WorkThread(InsertSrcDirThread):
	"""Thread that runs Worker while Tk keeps the GUI alive"""

	def __init__(self, gui: Gui) -> None:
		self._gui = gui
		super().__init__(daemon=True)
		self._kill_event = Event()
		self._gui.logger.add_remote(self._source)
		if self._gui.settings.user_log:
			self._gui.logger.add_user(self._gui.settings.user_log)
		self._worker = Worker(self._gui.source, self._gui.settings, kill=self._kill_event)

	def run(self) -> None:
		"""Run worker and report back to the GUI"""
		try:
			self._gui.finished(self._worker.run())
		except Exception as ex:
			return ex
