#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from time import strftime

class Logger:
	'''Configure Logging'''

	def __init__(self, config, labels, echo=print):
		'''Generate object to write log files'''
		self._config = config
		self._labels = labels
		self._echo = echo
		self._lastlog_path = self._config.local_path.joinpath(self._config.lastlog_name)
		self._remote = None
		self._user = None
		self._logger = logging.getLogger()
		self._logger.setLevel(logging.DEBUG)
		self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
		self._lastlog = self._add(self._lastlog_path, logging.DEBUG)
		logging.info(f'{self._labels.starting} "{self._labels.title}" v{self._labels.version}, {self._labels.user_label} "{self._labels.user}"')

	def _add(self, path, level):
		'''Add log file'''
		handler = logging.FileHandler(mode='w', filename=path)
		handler.setFormatter(self._formatter)
		handler.setLevel(level)
		self._logger.addHandler(handler)
		return handler

	def get_ts(self):
		'''Get timestamp'''
		return strftime('%y%m%d_%H%M%S')

	def add_remote(self, src_dir_path):
		'''Add remote log file'''
		self._remote_path = self._config.log_path.joinpath(src_dir_path.name, f'{self.get_ts()}_{self._config.log_name}')
		try:
			self._remote_path.parent.mkdir(parents=True, exist_ok=True)
			self._remote = self._add(self._remote_path, logging.DEBUG)
		except Exception as ex:
			self.crash(ex)
		else:
			logging.info(f'{self._labels.user_label} {self._labels.user}, {self._labels.source_dir}: {src_dir_path}')

	def close_remote(self):
		'''Close remote log file'''
		if self._remote:
			self._logger.removeHandler(self._remote)
			self._remote.close()

	def add_user(self, log_path, src_dir_paths):
		'''Add user log file with given path'''
		self._user_path = log_path.resolve()
		self._tmp_path = None
		for path in src_dir_paths:
			if self._user_path.is_relative_to(path):
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
				self._user_path.write_bytes(self._tmp_path.read_bytes())
				self._tmp_path.unlink()
			except Exception as ex:
				self.error(ex)

	def _decode(self, arg):
		'''Decode argument (Exception or text)'''
		if isinstance(arg, Exception):
			return f'{type(arg).__name__}: {arg}'
		return f'{arg}'

	def info(self, arg):
		'''Echo message abd log info'''
		msg = self._decode(arg)
		self._echo(msg)
		logging.info(msg)
		return msg

	def warning(self, arg):
		'''Echo message and log warning'''
		msg = self._decode(arg)
		self._echo(f'WARNING: {msg}')
		logging.warning(msg)
		return msg

	def error(self, arg):
		'''Log error'''
		msg = self._decode(arg)
		self._echo(f'ERROR: {msg}')
		logging.error(msg)
		return msg

	def crash(self, arg):
		'''Close all logs on crash and try to copy crashlog'''
		msg = self._decode(arg)
		self._echo(f'CRITICAL: {msg}')
		logging.critical(msg)
		self.close_remote()
		self.close_user()
		self._logger.removeHandler(self._lastlog)
		self._lastlog.close()
		logging.shutdown()
		self._config.log_path.joinpath(f'{self.get_ts()}_{self._config.crashlog_name}').write_bytes(self._lastlog_path.read_bytes())
		return msg

	def write_tsv(self, tsv, dst_path):
		'''Write TSV file'''
		name = f'{self.get_ts()}_{self._config.tsv_name}'
		self._remote_path.parent.joinpath(name).write_text(tsv, encoding='utf-8')
		dst_path.joinpath(name).write_text(tsv, encoding='utf-8')
