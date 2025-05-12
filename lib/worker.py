#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from time import strftime, sleep, perf_counter
from datetime import timedelta
from lib.robocopy import RoboCopy
from lib.hash import HashThread
from lib.size import Size
from lib.jsonmail import JsonMail

class Worker:
	'''Main functionality'''

	def __init__(self, app_path, config, labels,
		done=False, finished=True, log=None, trigger=True, kill=None, echo=print):
		'''Prepare copy process'''
		self._app_path = app_path
		self._config = config
		self._labels = labels
		self._send_done = done
		self._send_finished = finished
		self._write_trigger = trigger
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._config.user}@{self._config.domain}'
		try:
			logger = logging.getLogger()
			logger.setLevel(logging.DEBUG)
			self._formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
			local_log_fh = logging.FileHandler(
				mode = 'w',
				filename = log if log else app_path / self._config.log_name
			)
			local_log_fh.setFormatter(self._formatter)
			logger.addHandler(local_log_fh)
		except Exception as ex:
			echo(f'{type(ex)}: {ex}')
			raise ex
		try:
			self._robocopy = RoboCopy()
		except Exception as ex:
			self._error(ex)
			raise ex
	
	def copy_dir(self, src_path):
		'''Copy directories'''
		src_path = src_path.resolve()
		now = strftime('%y%m%d_%H%M')
		start_time = perf_counter()
		log_tsv_path = Path(self._config.log, src_path.name, f'{now}_{self._config.tsv_name}')
		logger = logging.getLogger()
		remote_log_fh = logging.FileHandler(
			mode = 'w',
			filename = Path(self._config.log, src_path.name, f'{now}_{self._config.log_name}')
		)
		remote_log_fh.setFormatter(self._formatter)
		logger.addHandler(remote_log_fh)
		logging.info(f'{self._mail_address} -> {self._config.destination}')
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
		dst_path = Path(self._config.target, src_path.name)
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
		try:
			log_tsv_path.write_text(tsv, encoding='utf-8')
		except Exception as ex:
			self._error(ex)
		if mismatches:
			raise BytesWarning(self._labels.size_mismatch.replace('#', f'{mismatches}'))
		if self._write_trigger:
			dst_path.joinpath(self._config.tsv_name).write_text(
				tsv, encoding='utf-8'
			)
		if self._send_done:
			dst_path.joinpath(self._config.done_name).write_text(
				self._mail_address, encoding='utf-8'
			)
		if self._send_finished:
			JsonMail(self._app_path / 'mail.json').send(
				Path(self._config.mail),
				to = self._mail_address,
				subject = src_path.name,
				body = tsv
			)
		end_time = perf_counter()
		delta = end_time - start_time
		self._info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=delta)}'))
		logger.removeHandler(remote_log_fh)

	def _info(self, msg):
		'''Log info and echo message'''
		logging.info(msg)
		self._echo(msg)

	def _error(self, ex):
		'''Log and echo error'''
		msg = f'{type(ex)}: {ex}'
		logging.error(msg)
		self._echo(msg)