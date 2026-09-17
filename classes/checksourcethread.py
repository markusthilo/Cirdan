#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from threading import Thread, Event
from tkinter.messagebox import askyesno
from classes.source import Source
from classes.logger import Logger as Log

class CheckSourceThread(Thread):
	'''Thread that checks if a directory is a valid source'''

	def __init__(self, source_dir, gui):
		'''Pass source directory to add to GUI'''
		self._gui = gui
		self._source = Source(source_dir,
			max_path_len = None if self._gui.no_source_check else self._gui.config.max_path_length,
			whitelist = None if self._gui.no_source_check else self._gui.config.source_whitelist,
			blacklist = None if self._gui.no_source_check else self._gui.config.source_blacklist
		)
		super().__init__()
		self._kill_event = Event()

	def run(self):
		'''Run thread to check and add source'''
		Log.info(self._gui.labels.checking_source.replace('#', f'{self._source}'))
		for path, bad in self._source.check():
			if self._kill_event.is_set():
				Log.debug(self._gui.labels.aborted_by_user)
				self._gui.abort_source_check()
				return
			self._gui.echo(f'{path}', end='\r')
			if isinstance(bad, int):
				msg = self._gui.labels.path_too_long.replace('#1', f'{path}').replace('#2', f'{bad}').replace('#3', f'{self._gui.config.max_path_length}')
				Log.warning(msg)
				if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_path_length}', default='no'):
					self._source.max_path_len = None
				else:
					self._gui.abort_source_check()
					return
			elif isinstance(bad, str):
				msg = self._gui.labels.blacklisted.replace('#1', f'{path}').replace('#2', f'{bad}')
				Log.warning(msg)
				if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_blacklist}', default='no'):
					self._source.blacklist = None
				else:
					self._gui.abort_source_check()
					return
		if not self._gui.no_source_check and not self._source.whitelist_match:
			msg = self._gui.labels.no_whitelist_match.replace('#', f'{self._source.path}')
			Log.warning(msg)
			if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_whitelist}', default='no'):
				self._source.whitelist = None
			else:
				self._gui.abort_source_check()
				return
		self._gui.add_source(self._source)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()
