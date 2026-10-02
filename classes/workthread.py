#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from threading import Thread, Event
from traceback import format_exc as get_exception
from classes.worker import Worker

class WorkThread(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Pass all attributes from GUI to work thread'''
		self._gui = gui
		super().__init__()
		self._kill_event = Event()
		self._worker = Worker(
			self._gui.sources,
			self._gui.todo,
			self._gui.config,
			self._gui.labels,
			self._gui.settings,
			self._gui.copy,
			self._gui.logger,
			user_log = self._gui.log_path,
			echo = self._gui.echo,
			kill = self._kill_event
		)

	def run(self):
		'''Run thread'''
		try:
			errors = self._worker.run()
		except:
			errors = [get_exception()]
		self._gui.finished(errors)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()
