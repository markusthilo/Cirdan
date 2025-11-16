#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from time import sleep, perf_counter
from datetime import timedelta
from os import getlogin
from classes.pathhandler import PathHandler
from classes.hash import HashThread
from classes.size import Size
from classes.jsonmail import JsonMail 

class Worker:
	'''Main functionality'''

	def __init__(self, src_paths, config, labels, settings, robocopy, logger, user_log=None, kill=None, echo=print):
		'''Prepare copy process'''
		self._config = config
		self._labels = labels
		self._settings = settings
		self._robocopy = robocopy
		self._logger = logger
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.user}@{self._config.domain}' if self._settings.user else None
		self._user = f'{self._labels.user} / {self._mail_address}' if self._mail_address else self._labels.user
		self._path_handler = PathHandler(self._config, self._labels)
		self._src_paths = list()
		logging.debug('Initializing worker')
		for path in src_paths:
			try:
				self._src_paths.append(self._path_handler.check_source_path(path))
			except Exception as ex:
				self._logger.error(ex)
		if user_log:
			try:
				self._logger.add_user(user_log, self._src_paths)
			except Exception as ex:
				self._logger.error(ex)

	def __del__(self):
		'''Close log file handler'''
		self._logger.close_remote()
		self._logger.close_user()

	def _copy_dir(self, src_path):
		'''Copy directories'''
		start_time = perf_counter()
		dst_path = self._path_handler.mk_destination(src_path, self._settings)
		self._logger.info(f'{self._labels.reading_structure} {src_path}')
		src_file_paths = list()
		src_file_sizes = list()
		total_bytes = 0
		for path in src_path.rglob('*'):	# analyze root structure
			if path.is_file():
				size = path.stat().st_size
				src_file_paths.append(path)
				src_file_sizes.append(size)
				total_bytes += size
		hash_thread = HashThread(src_file_paths)
		self._logger.info(self._labels.starting_hashing.replace('#', f'{len(src_file_paths)}'))
		hash_thread.start()
		dst_path = self._config.target_path.joinpath(self._config.destinations[self._settings.destination], src_path.name)
		self._logger.info(f'{self._labels.starting_robocopy}: {src_path} -> {dst_path}, {Size(total_bytes).readable()}')
		for line in self._robocopy.copy_dir(src_path, dst_path):
			if line.endswith('%'):
				self._echo(line, end='\r')
			else:
				self._echo(line)
			if self._kill_switch and self._kill_switch.is_set():
				self._robocopy.terminate()
				raise SystemExit(self._labels.worker_killed)
		try:
			robocopy_msg = f'{self._robocopy.returncode} - ' + self._labels.__dict__[f'returncode_{self._robocopy.returncode}']
		except KeyError:
			robocopy_msg = f'{self._robocopy.returncode}'
		robocopy_msg = self._labels.robocopy_returned.replace('#', robocopy_msg)
		if self._robocopy.returncode > 5:
			self._logger.warning(robocopy_msg)
		else:
			self._logger.info(robocopy_msg)
		self._logger.info(self._labels.starting_size_check)
		missing_paths = list()
		bad_paths = list()
		total = len(src_file_paths)
		for cnt, (src_file_path, src_size) in enumerate(zip(src_file_paths, src_file_sizes), start=1):
			self._echo(f'{int(100*cnt/total)}%', end='\r')
			dst_file_path = dst_path.joinpath(src_file_path.relative_to(src_path))
			if not dst_file_path.exists():
				self._logger.warning(self._labels.missing_file.replace('#', f'{src_file_path}'))
				missing_paths.append(src_file_path)
				continue
			dst_size = dst_file_path.stat().st_size
			if dst_size != src_size:
				self._warning(self._labels.mismatching_sizes.replace('#', f'{src_file_path} => {src_size}, {dst_file_path} => {dst_size}'))
				bad_paths.append(src_file_path)
		self._logger.info(self._labels.size_check_finished)
		if hash_thread.is_alive():
			self._info(self._labels.hashing_in_progress)
			index = 0
			while hash_thread.is_alive():
				self._echo(f'{"|/-\\"[index]}  ', end='\r')
				index += 1
				if index > 3:
					index = 0
				sleep(.25)
		hash_thread.join()
		self._logger.info(self._labels.hashing_finished)
		tsv = self._labels.tsv_head
		for path, md5 in hash_thread.get_hashes():
			tsv += f'\n{path.relative_to(src_path.parent)}\t{md5}\t'
			if path in missing_paths:
				tsv += self._labels.missing
			elif path in bad_paths:
				tsv += self._labels.bad_size
			else:
				tsv += self._labels.okay
		self._logger.write_tsv(tsv, dst_path)
		if missing_paths:
			raise FileNotFoundError(self._labels.error_missing.replace('#', f'{len(missing_paths)}'))
		if bad_paths:
			raise BytesWarning(self._labels.error_sizes.replace('#', f'{len(bad_paths)}'))
		if self._settings.trigger:
			dst_path.joinpath(self._config.trigger_name).write_text(self._user, encoding='utf-8')
		if self._settings.sendmail and self._mail_address:
			JsonMail(self._app_path / 'mail.json').send(
				self._config.mail_path.joinpath(f'{self._config.mail_name}_{now}.json'),
				to = self._mail_address,
				id = src_path.name,
				tsv = tsv
			)
		if self._settings.qualicheck:
			dst_path.joinpath(self._config.qualicheck_name).write_text(self._user, encoding='utf-8')
		end_time = perf_counter()
		delta = end_time - start_time
		self._logger.info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=delta)}'))

	def run(self):
		'''Start copy process'''
		for src_path in self._src_paths:
			if self._kill_switch and self._kill_switch.is_set():
				raise SystemExit(self._labels.worker_killed)
			try:
				self._logger.add_remote(src_path)
				#self._copy_dir(src_path)
			except Exception as ex:
				self._logger.error(ex)
			self._copy_dir(src_path)
			self._logger.close_remote()
		self._logger.close_user()