#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from os import getlogin
from platform import node
from traceback import format_exc
from sys import exc_info

class Logger:
	'''Configure Logging'''

	@staticmethod
	def debug(message):
		'''Log debug message'''
		logging.debug(message)

	@staticmethod
	def info(message):
		'''Log info message'''
		logging.info(message)

	@staticmethod
	def exception(level, message=None):
		'''Log exception'''
		msg_parts = list()
		if message:
			msg_parts.append(f'{message}' if message else '')
		ex_type, ex_text, traceback = exc_info()
		if ex_type:
			msg_parts.append(f'{ex_type.__name__}: {ex_text}')
		if traceback:
			msg_parts.append(f'{format_exc().strip()}')
		logging.__dict__[level.lower()](', '.join(msg_parts))

	@staticmethod
	def warning(message=None):
		'''Log warning'''
		Logger.exception('warning', message=message)

	@staticmethod
	def error(message=None):
		'''Log error'''
		Logger.exception('error', message=message)

	@staticmethod
	def critical(message=None):
		'''Log critical error'''
		Logger.exception('critical', message=message)

	def __init__(self, config, labels, echo=print):
		'''Generate object to write log files'''
		self._config = config
		self._labels = labels
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		self._echo_handler = self.set_echo(echo=echo)
		self._config.local_path.mkdir(parents=True, exist_ok=True)
		self._lastlog_path = self._config.local_path.joinpath(self._config.lastlog_name)
		self._lastlog_handler = self.add_file(self._lastlog_path)
		self._remote_path = None
		self._remote_handler = None
		self._user_path = None
		self._user_handler = None
		self._user_messages = list()
		self.login = getlogin()
		self.node = node()
		self.basic_info = f'{self._labels.hostname}: {self.node}, {self._labels.username}: {self.login}, {self._labels.title} v{self._labels.version}'
		self.debug(f'{self.basic_info} {self._labels.launched}')

	def add_file(self, path, level=logging.DEBUG):
		'''Add log file'''
		handler = logging.FileHandler(mode='w', filename=path)
		handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
		handler.setLevel(level)
		self._logger.addHandler(handler)
		return handler

	def set_echo(self, echo=print):
		'''Set how to echo messages'''
		level = logging.INFO
		class echo_stream:	# stream handler using echo
			def write(msg):
				echo(msg.strip())
		try:
			if self._echo_handler:
				level = self._echo_handler.level
				self._logger.removeHandler(self._echo_handler)
				self._echo_handler.close()
		except:
			pass
		self._echo_handler = logging.StreamHandler(stream=echo_stream)
		self._echo_handler.setLevel(level)
		self._logger.addHandler(self._echo_handler)

	def add_user(self, path, level=logging.INFO):
		'''Add user log, logs to RAM / variable until closing'''
		class store_stream:	# stream handler using self._user_messages
			def write(msg):
				self._user_messages.append(msg.strip())
		self.debug(f'Setting up user log, path: {path}')
		self._user_path = path.resolve()
		self._user_handler = logging.StreamHandler(stream=store_stream)
		self._user_handler.setLevel(level)
		self._logger.addHandler(self._user_handler)
		self.info(f'{self.basic_info}, {self._labels.logfile}')

	def close_user(self):
		'''Close user log'''
		if not self._user_handler:
			return
		self._logger.removeHandler(self._user_handler)
		self._user_handler.close()
		logging.debug('Closing user log')
		self._user_path.write_text('\n'.join(self._user_messages), encoding='utf-8')

	def add_remote(self, source, destination):
		'''Add remote log file'''
		msg = f'{self.basic_info}, {self._labels.source_dir}: {source}, {self._labels.destination}: {destination}'
		self._remote_path = self._config.log_path.joinpath(source.name, self._config.log_name).timed()
		try:
			self._remote_path.parent.mkdir(parents=True, exist_ok=True)
			self._remote_handler = self.add_file(self._remote_path)
			self.debug(msg)
		except:
			try:
				self._remote_handler.close()
			except:
				pass
			try:
				self.error()
			except:
				pass
			self._remote_path = self._config.log_path.joinpath(f'{source.name}_{self._config.log_name}').timed()
			try:
				self._remote_path.parent.mkdir(parents=True, exist_ok=True)
				self._remote_handler = self.add_file(self._remote_path)
				self.debug(msg)
			except:
				return self.error()

	def get_remote_parent(self):
		'''Get parent of remote log file'''
		if self._remote_path:
			return self._remote_path.parent

	def close_remote(self):
		'''Close remote log file'''
		self.debug(f'Closing remote log, path: {self._remote_path}')
		if self._remote_handler:
			self._logger.removeHandler(self._remote_handler)
			self._remote_handler.close()

	def crash(self, message=None):
		'''Close all logs on crash and try to copy crashlog'''
		self.critical(message=message)
		self.close_remote()
		self.close_user()
		self._logger.removeHandler(self._lastlog_handler)
		self._lastlog_handler.close()
		logging.shutdown()
		try:
			self._lastlog_path.copy(self._config.log_path.joinpath(self._config.crashlog_name).timed())
		except:
			pass
		return message
