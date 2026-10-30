#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from tkinter.messagebox import askyesno
from classes.source import Source
from classes.logger import Logger as Log
from classes.gimmicks import IndicatorThread
from classes.path import Path
if TYPE_CHECKING:
	from classes.gui import Gui

class CheckSourceThread(Thread):
	"""Thread that checks if a directory is a valid source"""

	def __init__(self, gui: Gui, source_dir: Path) -> None:
		"""Pass source directory to add to GUI"""
		self._gui = gui
		self._source = Source(source_dir, self._gui.settings)
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

	def _stop_indicator(self, indicator: IndicatorThread) -> None:
		"""Stop the busy indicator"""
		indicator.kill()
		indicator.join(timeout=1)

	def run(self) -> None:
		"""Run thread to check and add source"""
		labels = self._gui.labels
		settings = self._gui.settings
		Log.info(labels.checking_source.replace("#", f"{self._source}"))
		self._gui.echo(labels.checking_source.replace("#", f"{self._source}"))
		indicator = IndicatorThread(message=None, indicator="cylon", echo=self._gui.echo)
		indicator.daemon = True
		indicator.start()
		try:
			for path, bad in self._source.check(kill=self._kill_event):
				if self._kill_event.is_set():
					return
				if isinstance(bad, int):
					msg = (
						labels.path_too_long
						.replace("#1", f"{path}")
						.replace("#2", f"{bad}")
						.replace("#3", f"{settings.max_path_length}")
					)
					Log.warning(msg)
					if self._askyesno(
						labels.warning,
						f"{msg}\n\n{labels.ignore_path_length}",
					):
						self._source.disable_path_length_check()
					else:
						self._gui.abort_source_check()
						return
				elif isinstance(bad, str):
					msg = (
						labels.blacklisted
						.replace("#1", f"{path}")
						.replace("#2", f"{bad}")
					)
					Log.warning(msg)
					if self._askyesno(
						labels.warning,
						f"{msg}\n\n{labels.ignore_blacklist}",
					):
						self._source.disable_blacklist()
					else:
						self._gui.abort_source_check()
						return
			if self._kill_event.is_set():
				return
			self._gui.add_source(self._source)
		except Exception:
			Log.error()
			self._gui.abort_source_check()
		finally:
			self._stop_indicator(indicator)

	def kill(self) -> None:
		"""Kill thread"""
		self._kill_event.set()
