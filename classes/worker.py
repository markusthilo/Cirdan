#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from time import strftime, sleep, perf_counter
from datetime import timedelta
from os import getlogin
from classes.pathhandler import PathHandler
from classes.robocopy import RoboCopy
from classes.hash import HashThread
from classes.size import Size
from classes.jsonmail import JsonMail 

class Worker:
	'''Main functionality'''

	def __init__(self, app_path, config, labels, settings, local_log=None, kill=None, echo=print):
		'''Prepare copy process'''
		self._app_path = app_path
		self._config = config
		self._settings = settings
		self._local_log_path = local_log
		self._labels = labels
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.user}@{self._config.domain}' if self._settings.user else None
		self._user = getlogin()
		if self._mail_address:
			self._user += f' / {self._mail_address}'
		self._path_handler = PathHandler(self._config, self._labels)
		self._lastlog_path = self._config.local_path / 'lastlog.txt'
		try:
			self._logger = logging.getLogger()
			self._logger.setLevel(logging.DEBUG)
			self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
			self._lastlog_fh = logging.FileHandler(mode='w', filename=self._lastlog_path)
			self._lastlog_fh.setFormatter(self._formatter)
			self._logger.addHandler(self._lastlog_fh)
		except Exception as ex:
			self._echo(f'{self._labels.error}: {type(ex)}: {ex}')
			raise ex
		try:
			self._robocopy = RoboCopy()
		except Exception as ex:
			self._error(ex)

	def __del__(self):
		'''Close log file handler'''
		logging.shutdown()
		if self._local_log_path:
			self._local_log_path.write_text(self._lastlog_path.read_text())

	
	def copy_dir(self, src_path):
		'''Copy directories'''
		start_time = perf_counter()
		now = strftime('%y%m%d_%H%M%S')
		src_path = src_path.resolve()
		remote_log_dir_path = self._config.log_path / src_path.name
		remote_log_dir_path.mkdir(parents=True, exist_ok=True)
		self._remote_log_fh = logging.FileHandler(mode='w', filename=remote_log_dir_path /  f'{now}_{self._config.log_name}')
		self._remote_log_fh.setFormatter(self._formatter)
		self._logger.addHandler(self._remote_log_fh)
		logging.info(f'{self._labels.user_label}: {self._user}')
		try:
			dst_path = self._path_handler.mk_destination(src_path, self._settings)
		except Exception as ex:
			self._error(ex)
		self._info(f'{self._labels.reading_structure} {src_path}')
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
		self._info(self._labels.starting_hashing.replace('#', f'{len(src_file_paths)}'))
		hash_thread.start()
		dst_path = self._config.target_path.joinpath(self._config.destinations[self._settings.destination], src_path.name)
		self._info(f'{self._labels.starting_robocopy}: {src_path} -> {dst_path}, {Size(total_bytes).readable()}')
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
			self._warning(robocopy_msg)
		else:
			self._info(robocopy_msg)
		self._info(self._labels.starting_size_check)
		missing_paths = list()
		bad_paths = list()
		total = len(src_file_paths)
		for cnt, (src_file_path, src_size) in enumerate(zip(src_file_paths, src_file_sizes), start=1):
			self._echo(f'{int(100*cnt/total)}%', end='\r')
			dst_file_path = dst_path.joinpath(src_file_path.relative_to(src_path))
			if not dst_file_path.exists():
				self._warning(self._labels.missing_file.replace('#', f'{src_file_path}'))
				missing_paths.append(src_file_path)
				continue
			dst_size = dst_file_path.stat().st_size
			if dst_size != src_size:
				self._warning(self._labels.mismatching_sizes.replace('#', f'{src_file_path} => {src_size}, {dst_file_path} => {dst_size}'))
				bad_paths.append(src_file_path)
		self._info(self._labels.size_check_finished)
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
		self._info(self._labels.hashing_finished)
		tsv = self._labels.tsv_head
		for path, md5 in hash_thread.get_hashes():
			tsv += f'\n{path.relative_to(src_path.parent)}\t{md5}\t'
			if path in missing_paths:
				tsv += self._labels.missing
			elif path in bad_paths:
				tsv += self._labels.bad_size
			else:
				tsv += self._labels.okay
		tsv_name =  f'{now}_{self._config.tsv_name}'
		self._config.log_path.joinpath(src_path.name, tsv_name).write_text(tsv, encoding='utf-8')
		dst_path.joinpath(tsv_name).write_text(tsv, encoding='utf-8')
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
		self._info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=delta)}'))
		self._logger.removeHandler(self._remote_log_fh)

	def _info(self, msg):
		'''Log info and echo message'''
		logging.info(msg)
		self._echo(msg)

	def _warning(self, msg):
		'''Log warning and echo message'''
		logging.warning(msg)
		self._echo(msg)

