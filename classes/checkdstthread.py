#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from threading import Thread, Event
from classes.destination import Destination
from classes.path import Path

class CheckDstThread(Thread):
	'''Thread that checks the destination directory'''

	def __init__(self, gui):
		'''Pass all attributes from GUI to work thread'''
		self._gui = gui
		super().__init__()
		self._kill_event = Event()
		self._destination = Destination(
			Path(self._gui.config.target_path).joinpath(
				self._gui.config.destinations[self._gui.destination.get()]['sub_path']),
			self._gui.config.source_whitelist,
			self._gui.config.destination_blacklist
		)

	def run(self):
		'''Run thread'''
		try:
			for sub_dir in self._destination.check():
				if self._kill_event.is_set():
					break
				self._gui.echo(f'{{self._gui.labels.checking}} {sub_dir}')
		except:
			self_gui.logger.error()
		self._gui.open_todo_dialog(self._destination)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()
