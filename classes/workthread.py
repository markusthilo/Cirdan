#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from threading import Thread, Event
from traceback import format_exc
from classes.worker import Worker
if TYPE_CHECKING:
	from classes.gui import Gui

class WorkThread(Thread):
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

	def kill(self) -> None:
		"""Ask the worker to stop"""
		self._kill_event.set()
