#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from tkinter.messagebox import askyesno
from classes.logger import Logger as Log
from classes.gimmicks import Cylon
from traceback import format_exc
if TYPE_CHECKING:
	from classes.gui import Gui
	from classes.path import Path

class AddSubDirThread(Thread):
	"""Thread to add a sub directory into source"""

	def __init__(self, gui: Gui, arg: Path | str) -> None:
		self._gui = gui
		self._dir_path = self._gui.source.sub_dir(arg)
		if not self._dir_path:
			msg = self._gui.labels.not_a_valid_directory.replace("#", str(arg))
			raise ValueError(msg) from None
		if dir_name := self._gui.source.sub_dir_already_set(self._sub_dir):
			msg = self._gui.labels.sub_dir_already_set.replace("#", dir_name)
			raise ValueError(msg) from None
		self._insert = self._gui.source.add_sub_dir
		self._indicator = Cylon()
		super().__init__(daemon=True)
		self._kill_event = Event()
		self.returncode = None

	def _warning_yesno(self, message: str) -> bool:
		"""Show askyesno on the Tk main thread and wait for the answer"""
		result: list[bool] = []
		done = Event()
		def ask() -> None:
			try:
				self._gui._prepare_dialog()
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
		Log.debug(f"{self._labels.checking} {self._dir_path}")
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
				self.returncode

	def kill(self) -> None:
		"""Kill thread"""
		self._kill_event.set()

class InsertTopDirThread(AddSubDirThread):
	"""Thread to insert the top directory into source"""

	def __init__(self, gui: Gui, arg: Path | str) -> None:
		self._gui = gui
		self._dir_path = self._gui.source.top_dir(arg)
		if not self._dir_path:
			msg = self._gui.labels.not_a_valid_directory.replace("#", str(arg))
			raise ValueError(msg) from None
		self._insert = self._gui.source.insert_top_dir
		self._indicator = Cylon()
		super().__init__(daemon=True)
		self._kill_event = Event()

class WorkThread(AddSubDirThread):
	"""Thread that runs Worker while Tk keeps the GUI alive"""

	def __init__(self, gui: Gui) -> None:
		self._gui = gui
		super().__init__(daemon=True)
		self._kill_event = Event()
		user_log = None
		if self._gui.write_log.get():
			user_log = self._gui.log_path or self._gui.settings.user_log
		self._worker = Worker(
			list(self._gui.sources),
			self._gui.settings,
			self._gui.logger,
			user_log=user_log,
			echo=self._gui.echo,
			kill=self._kill_event,
		)

	def run(self) -> None:
		"""Run worker and report back to the GUI"""
		try:
			errors = self._worker.run()
		except Exception:
			errors = [format_exc()]
		self._gui.finished(errors)

