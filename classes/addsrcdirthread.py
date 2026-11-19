#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from tkinter.messagebox import askyesno
from classes.logger import Logger as Log
from classes.gimmicks import Cylon
if TYPE_CHECKING:
	from classes.gui import Gui
	from classes.path import Path

class AddSubDirThread(Thread):
	"""Thread to insert a sub directory into source, top or sub level"""

	def __init__(self, gui: Gui, arg: Path | str) -> None:
		"""Pass source sub directory to add to GUI"""
		self._gui = gui
		self._sub_dir = self._gui.source.sub_dir(arg)
		if not self._sub_dir:
			msg = self._gui.labels.not_a_valid_directory.replace("#", str(arg))
			raise ValueError(msg) from None
		if dir_name := self._gui.source.sub_dir_already_set(self._sub_dir):
			msg = self._gui.labels.sub_dir_already_set.replace("#", dir_name)
			raise ValueError(msg) from None
		self._indicator = Cylon()
		super().__init__(daemon=True)
		self._kill_event = Event()

	def _askyesno(self, title: str, message: str, default: str = "no") -> bool:
		"""Show askyesno on the Tk main thread and wait for the answer"""
		result: list[bool] = []
		done = Event()

		def ask() -> None:
			try:
				self._gui._prepare_dialog()
				result.append(askyesno(
					parent=self._gui,
					title=title,
					message=message,
					default=default,
				))
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
		Log.debug(f"{self._labels.checking} {self._sub_dir}")
		for rel_path, error in self._gui.source.add_sub_dir(self._sub_dir):
			if self._kill_event.is_set():
				return
			self._gui.echo(self._indicator.get(), end="\r")
			if error:
				if isinstance(error, int):
					pass
				elif isinstance(error, str):
					pass

	def kill(self) -> None:
		"""Kill thread"""
		self._kill_event.set()
