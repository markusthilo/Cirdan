#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from tkinter.messagebox import askyesno
from classes.source import Source
from classes.logger import Logger as Log
from classes.gimmicks import Cylon
from classes.path import Path
if TYPE_CHECKING:
	from classes.gui import Gui

class AddSrcDirThread(Thread):
	"""Thread to insert a directory into source, top or sub level"""

	def __init__(self, gui: Gui, path: Path) -> None:
		"""Pass source directory to add to GUI"""
		self._gui = gui
		self._top_dir_name: str | None = self._source.top_dir(path)
		self._sub_dir_name: str | None = self._source.sub_dir(path)
		if not self._top_dir_name and not self._sub_dir_name:
			raise ValueError(self._labels.not_a_valid_directory.replace("#", str(path)))
		self._path: Path = path
		self._worker = self._source.insert_top_dir if self._top_dir_name else self._source.add_sub_dir
		self._initial_indicator = Cylon()
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

	def _check_for_error(self, rel_path: Path, error: int | str) -> None:
		"""Add sub directory to source"""
		if error:
			if isinstance(error, int):
				pass
			elif isinstance(error, str):
				pass

	def run(self) -> None:
		"""Run thread to check and add source"""
		msg = self._labels.checking_source.replace("#", f"{self._source.name}")
		Log.info(msg)
		self._gui.echo(msg)
		for rel_path, error in self._worker(self._path):
			if self._kill_event.is_set():
				return
			self._gui.echo(self._indicator.get(), end="\r")
			self._check_for_error(rel_path, error)

	def kill(self) -> None:
		"""Kill thread"""
		self._kill_event.set()
