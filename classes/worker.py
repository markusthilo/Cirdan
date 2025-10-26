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
		self._labels = labels
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.user}@{self._config.domain}' if self._settings.user else None
		self._user = getlogin()
		if self._mail_address:
			self._user += f' / {self._mail_address}'
		self._path_handler = PathHandler(self._config, self._labels)
		try:
			self._logger = logging.getLogger()
			self._logger.setLevel(logging.DEBUG)
			self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
			self._local_log_fh = logging.FileHandler(
				mode = 'w',
				filename = local_log if local_log else self._config.local_path / self._config.log_name
			)
			self._local_log_fh.setFormatter(self._formatter)
			self._logger.addHandler(self._local_log_fh)
		except Exception as ex:
			echo(f'{self._labels.error}: {type(ex)}: {ex}')
			raise ex
		try:
			self._robocopy = RoboCopy()
		except Exception as ex:
			self._error(ex)

	def __del__(self):
		'''Close log file handler'''
		try:
			self._logger.removeHandler(self._local_log_fh)
		except:
			pass
		try:
			self._logger.removeHandler(self._remote_log_fh)
		except:
			pass
		try:
			logging.shutdown()
		except:
			pass
	
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
		if self._robocopy.returncode > 5:
			raise ChildProcessError(self._labels.robocopy_problem.replace('#', f'{self._robocopy.returncode}'))
		self._info(self._labels.robocopy_finished)
		mismatches = 0
		total = len(src_file_paths)
		for cnt, (src_file_path, src_size) in enumerate(zip(src_file_paths, src_file_sizes), start=1):
			self._echo(f'{int(100*cnt/total)}%', end='\r')
			dst_file_path = dst_path.joinpath(src_file_path.relative_to(src_path))
			dst_size = dst_file_path.stat().st_size
			if dst_size != src_size:
				msg = self._labels.mismatching_sizes.replace('#', f'{src_file_path} => {src_size}, {dst_file_path} => {dst_size}')
				logging.warning(msg)
				self._echo(msg)
				mismatches += 1
		self._info(self._labels.size_check_finished)
		if hash_thread.is_alive():
			self._info(self._labels.hashing_in_progress)
			index = 0
			while hash_thread.is_alive():
				echo(f'{"|/-\\"[index]}  ', end='\r')
				index += 1
				if index > 3:
					index = 0
				sleep(.25)
		hash_thread.join()
		self._info(self._labels.hashing_finished)
		tsv = self._config.tsv_head
		for path, md5 in hash_thread.get_hashes():
			tsv += f'\n{path.relative_to(src_path.parent)}\t{md5}'
		tsv_name =  f'{now}_{self._config.tsv_name}'
		try:
			self._config.log_path.joinpath(src_path.name, tsv_name).write_text(tsv, encoding='utf-8')
		except Exception as ex:
			self._error(ex)
		try:
			dst_path.joinpath(tsv_name).write_text(tsv, encoding='utf-8')
		except Exception as ex:
			self._error(ex)
		if mismatches:
			self._error(BytesWarning(self._labels.mismatching_sizes.replace('#', f'{mismatches}')))
		if self._settings.trigger:
			try:
				dst_path.joinpath(self._config.trigger_name).write_text(self._user, encoding='utf-8')
			except Exception as ex:
				self._error(ex)
		if self._settings.sendmail and self._mail_address:
			try:
				JsonMail(self._app_path / 'mail.json').send(
					self._config.mail_path.joinpath(f'{self._config.mail_name}_{now}'),
					to = self._mail_address,
					id = src_path.name,
					tsv = tsv
				)
			except Exception as ex:
				self._error(ex)
		if self._settings.qualicheck:
			try:
				dst_path.joinpath(self._config.qualicheck_name).write_text(self._user, encoding='utf-8')
			except Exception as ex:
				self._error(ex)
		end_time = perf_counter()
		delta = end_time - start_time
		self._info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=delta)}'))
		self._logger.removeHandler(self._remote_log_fh)

	def _info(self, msg):
		'''Log info and echo message'''
		logging.info(msg)
		self._echo(msg)

	def _error(self, ex):
		'''Log and echo error'''
		msg = f'{type(ex)}: {ex}'
		logging.error(msg)
		self._echo(f'{self._labels.error}: {msg}')
		raise ex
