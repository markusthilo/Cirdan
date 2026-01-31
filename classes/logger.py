#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from os import getlogin
from platform import node
from traceback import format_exc
from sys import exc_info

class Logger:
	'''Configure Logging'''

	def __init__(self, config, labels, echo=print):
		'''Generate object to write log files'''
		self._config = config
		self._labels = labels
		self._echo = echo
		self._config.local_path.mkdir(parents=True, exist_ok=True)
		self._lastlog_path = self._config.local_path.joinpath(self._config.lastlog_name)
		self._remote = None
		self._user = None
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
		self._lastlog = self._add(self._lastlog_path, logging.DEBUG)
		self.login = getlogin()
		self.node = node()
		self.basic_info = f'{self._labels.hostanme}: {self.node}, {self._labels.username}: {self.login}, {self._labels.title} v{self._labels.version}'
		logging.debug(f'{self.basic_info} {self._labels.launched}')

	def _add(self, path, level):
		'''Add log file'''
		handler = logging.FileHandler(mode='w', filename=path)
		handler.setFormatter(self._formatter)
		handler.setLevel(level)
		self._logger.addHandler(handler)
		return handler

	def set_echo(self, method):
		'''Set how to echo messages'''
		self._echo = method

	def add_remote(self, src_dir_path, dst_root_path):
		'''Add remote log file'''
		msg = f'{self.basic_info}, {self._labels.source_dir}: {src_dir_path}, {self._labels.destination}: {dst_root_path}'
		self._remote_path = self._config.log_path.joinpath(f'{dst_root_path.name}', src_dir_path.name, self._config.log_name).timed()
		try:
			self._remote_path.parent.mkdir(parents=True, exist_ok=True)
			self._remote = self._add(self._remote_path, logging.DEBUG)
			logging.debug(msg)
		except:
			try:
				self.warning(self._labels.log_error.replace('#', f'{ex}'))
			except:
				pass
			try:
				self._remote.close()
			except:
				path
			self._remote_path = self._config.log_path.joinpath(f'{dst_root_path.name}', f'{src_dir_path.name}_{self._config.log_name}').timed()
			try:
				self._remote_path.parent.mkdir(parents=True, exist_ok=True)
				self._remote = self._add(self._remote_path, logging.DEBUG)
				logging.debug(msg)
			except:
				return self.error(self._labels.log_error.replace('#', f'{ex}'))

	def get_remote_parent(self):
		'''Get parent of remote log file'''
		if self._remote:
			return self._remote_path.parent

	def close_remote(self):
		'''Close remote log file'''
		if self._remote:
			self._logger.removeHandler(self._remote)
			self._remote.close()

	def add_user(self, log_path, sources):
		'''Add user log file with given path if not inside path to copy'''
		self._user_path = log_path.resolve()
		self._tmp_path = None
		for source in sources:
			if self._user_path.is_relative_to(source.path):
				self._tmp_path = self._config.local_path.joinpath(self._config.tmplog_name)
				log_path = self._tmp_path
				break
		self._user = self._add(log_path, logging.INFO)

	def close_user(self):
		'''Close user log'''
		if not self._user:
			return
		logging.debug('Closing user log')
		self._logger.removeHandler(self._user)
		self._user.close()
		if self._tmp_path:
			try:
				self._tmp_path.move(self._user_path)
			except:
				self.error()

	def _decode(self, *arg):
		'''Decode argument (Exception or text)'''
		if isinstance(arg, RuntimeError):
			return f'{arg}'
		if not arg or isinstance(arg, Exception):
			ex_type, ex_text, traceback = exc_info()
			return f'{ex_text}\n\n{format_exc().strip()}'
		return f'{arg}'

	def info(self, arg):
		'''Echo message abd log info'''
		msg = self._decode(arg)
		self._echo(msg)
		logging.info(msg)
		return msg

	def warning(self, *arg):
		'''Echo message and log warning'''
		msg = self._decode(*arg)
		self._echo(f'WARNING: {msg}')
		logging.warning(msg)
		return msg

	def error(self, *arg):
		'''Log error'''
		msg = self._decode(*arg)
		self._echo(f'ERROR: {msg}')
		logging.error(msg)
		return msg

	def crash(self, *arg):
		'''Close all logs on crash and try to copy crashlog'''
		msg = self._decode(*arg)
		self._echo(f'CRITICAL: {msg}')
		logging.critical(msg)
		self.close_remote()
		self.close_user()
		self._logger.removeHandler(self._lastlog)
		self._lastlog.close()
		logging.shutdown()
		try:
			self._config.log_path.joinpath(f'{self.login}_{self._config.crashlog_name}').timed().write_bytes(self._lastlog_path.read_bytes())
		except:
			pass
		return msg
