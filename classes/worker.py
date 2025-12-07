#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from time import sleep, perf_counter
from datetime import timedelta
from classes.paths import PathTree
from classes.hash import HashThread
from classes.size import Size
from classes.jsonmail import JsonMail 

class Worker:
	'''Main functionality'''

	def __init__(self, src_paths, config, labels, settings, robocopy, logger, user_log=None, kill=None, echo=print):
		'''Prepare copy process'''
		self._src_paths = src_paths
		self._config = config
		self._labels = labels
		self._settings = settings
		self._robocopy = robocopy
		self._logger = logger
		self._user_log = user_log
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.user}@{self._config.domain}' if self._settings.user else None
		self._user = f'{self._labels.user} / {self._mail_address}' if self._mail_address else self._labels.user
		self.errors = list()

	def _error(self, arg):
		'''Handle error'''
		self.errors.append(self._logger.error(arg))

	def _copy(self, source, destination):
		'''Copy directory'''
		start_time = perf_counter()
		self._logger.info(f'{self._labels.reading_structure} {source}')
		src_file_paths = list()
		src_file_sizes = list()
		total_bytes = Size(0)
		for path in source.walk():	# analyze root structure
			if path.is_file():
				size = path.stat().st_size
				src_file_paths.append(path)
				src_file_sizes.append(size)
				total_bytes += size
		hash_thread = HashThread(src_file_paths)
		self._logger.info(self._labels.starting_hashing.replace('#', f'{len(src_file_paths)}'))
		hash_thread.start()
		self._logger.info(f'{self._labels.starting_robocopy}: {source} -> {destination}, {total_bytes.readable()}')
		for line in self._robocopy.copy_dir(source, destination):
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
			dst_file_path = destination.joinpath(source.get_relative(src_file_path))
			if not dst_file_path.exists():
				self._logger.warning(self._labels.missing_file.replace('#', f'{src_file_path}'))
				missing_paths.append(src_file_path)
				continue
			dst_size = dst_file_path.stat().st_size
			if dst_size != src_size:
				self._logger.warning(self._labels.mismatching_sizes.replace('#', f'{src_file_path} => {src_size}, {dst_file_path} => {dst_size}'))
				bad_paths.append(src_file_path)
		self._logger.info(self._labels.size_check_finished)
		if hash_thread.is_alive():
			self._logger.info(self._labels.hashing_in_progress)
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
			tsv += f'\n{path.relative_to(source.parent)}\t{md5}\t'
			if path in missing_paths:
				tsv += self._labels.missing
			elif path in bad_paths:
				tsv += self._labels.bad_size
			else:
				tsv += self._labels.okay
		self._logger.write_tsv(tsv, destination)
		if missing_paths:
			self._error(self._labels.error_missing.replace('#', f'{len(missing_paths)}'))
		if bad_paths:
			self._error(self._labels.error_sizes.replace('#', f'{len(bad_paths)}'))
		time_delta = perf_counter() - start_time
		self._logger.info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=time_delta)}'))

	def run(self):
		'''Start copy process'''
		logging.debug('Running worker')
		sources = list()
		for src_path in self._src_paths:
			source = PathTree(src_path)
			match, pattern = source.search(self._config.source_whitelist)
			if not match:
				self._error(self._labels.bad_source.replace('#', f'{source}'))
				continue
			match, length = source.too_long(self._config.max_path_length)
			if match:
				self._error(self._labels.path_too_long.replace(
					'#1', f'{match}').replace(
					'#2', f'{length}').replace(
					'#3', f'{self._config.max_path_length}')
				)
				continue
			if not self._settings.tolerant:
				match, pattern = source.search(self._config.source_blacklist)
				if match:
					self._error(self._labels.blacklisted.replace('#1', f'{match}').replace('#2', f'{pattern}'))
					continue
			sources.append(source)
		if not sources:
			self._error(self._labels.no_sources)
			return self.errors
		if self._user_log:
			try:
				self._logger.add_user(self._user_log, sources)
			except Exception as ex:
				self._logger.warning(self._labels.log_error.replace('#', f'{ex}'))
		self._destination_root_path = self._config.target_path.joinpath(self._config.destinations[self._settings.destination])
		if not self._destination_root_path.is_accessable_dir():
			self._error(self._labels.bad_destination.replace('#', f'{self._destination_root_path}'))
			return
		for source in sources:
			if self._kill_switch and self._kill_switch.is_set():
				raise SystemExit(self._labels.worker_killed)
			destination = PathTree(self._destination_root_path / source.name)
			try:
				new = destination.mk()
			except Exception as ex:
				self._error(ex)
				continue
			if new:
				match, pattern = destination.search(self._config.source_blacklist)
				if match:
					self._error(self._labels.destination_blocked_by.replace('#1', f'{match}').replace('#2', f'{pattern}'))
					continue
			try:
				self._logger.add_remote(src_path)
			except Exception as ex:
				self._error(self._labels.log_error.replace('#', f'{ex}'))
			try:
				self._copy(source, destination)
			except Exception as ex:
				self._error(ex)
			if self._settings.trigger:
				try:
					destination.write_text_file(self._config.trigger_name, self._user)
				except Exception as ex:
					self._error(ex)
			if self._settings.qualicheck:
				try:
					destination.write_text_file(self._config.qualicheck_name, self._user)
				except Exception as ex:
					self._error(ex)
			if self._settings.sendmail and self._mail_address:
				try:
					JsonMail(self._config.app_path / 'mail.json').send(
						self._config.mail_path.joinpath(f'{self._config.mail_name}_{self._logger.get_ts()}_{self._labels.user}.json'),
						to = self._mail_address,
						id = source.name,
						tsv = tsv
					)
				except Exception as ex:
					self._error(ex)
			try:
				self._logger.close_remote()
			except Exception as ex:
				self._logger.warning(ex)
		try:
			self._logger.close_user()
		except Exception as ex:
			self._logger.warning(ex)
		return self.errors
