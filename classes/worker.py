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
		self._id = f'{self._labels.username}: {self._logger.login}\n{self._labels.hostanme}: {self._logger.node}'
		self.errors = list()

	def _error(self, *arg):
		'''Handle error'''
		self.errors.append(self._logger.error(*arg))

	def run(self):
		'''Start copy process'''
		start_time = perf_counter()
		logging.debug('Running worker')
		destination_root_path = self._config.target_path.joinpath(self._config.destinations[self._settings.destination])
		if not destination_root_path.is_accessable_dir():
			self._error(self._labels.bad_destination.replace('#', f'{destination_root_path}'))
			return self.errors
		sources = list()
		for src_path in self._src_paths:	# check given source paths
			source = PathTree(src_path)
			try:
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
			except:
				self._error()
		if not sources:
			self._error(self._labels.no_sources)
			return self.errors
		if self._user_log:	# start additional log if selected
			try:
				self._logger.add_user(self._user_log, sources)
			except Exception as ex:
				self._logger.warning(self._labels.log_error.replace('#', f'{ex}'))
		for source in sources:	# copy source after source
			if self._kill_switch and self._kill_switch.is_set():
				raise SystemExit(self._labels.worker_killed)
			destination = PathTree(destination_root_path / source.name)
			try:	# create new destination direcgtory if not already there
				new = destination.mk()
			except:
				self._error()
				continue
			self._logger.info(self._labels.checking_source.replace('#', f'{source}'))
			if not new:	# check for blacklisted files in destination
				match, pattern = destination.search(self._config.destination_blacklist)
				if match:
					self._error(self._labels.destination_blocked_by.replace('#1', f'{match}').replace('#2', f'{pattern}'))
					continue
			if error := self._logger.add_remote(src_path, destination_root_path):	# add log for one source / one destination
				self.errors.append(error)
				continue
			try:
				source.walk_files()
			except:
				self._error()
				continue
			self._logger.info(self._labels.found_files_in_source.replace(
				'#1', f'{source.total_files}').replace(
				'#2', f'{source}').replace(
				'#3', f'{source.total_bytes.readable()}')
			)
			try:
				hash_thread = HashThread(source.parent, source.rel_file_paths)	# start hashing
				self._logger.info(self._labels.starting_hashing)
				hash_thread.start()
				self._logger.info(f'{self._labels.starting_robocopy}: {source} -> {destination}, {source.total_bytes.readable()}')
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
				self._logger.info(self._labels.starting_size_check)	# size check
				rel_paths = list()
				missing_paths = 0
				bad_paths = 0
				for cnt, (rel_path, src_size) in enumerate(source.get_rel_paths_sizes(), start=1):
					self._echo(f'{int(100*cnt/source.total_files)}%', end='\r')
					dst_size = destination.check_file(rel_path)
					if dst_size == None:
						self._logger.warning(self._labels.missing_file.replace('#', f'{rel_path}'))
						missing_paths += 1
						rel_paths.append((rel_path, src_size, None, False))
					elif dst_size != src_size:
						self._logger.warning(self._labels.mismatching_sizes.replace('#', f'{rel_path} => {src_size}, {rel_path} => {dst_size}'))
						bad_paths += 1
						rel_paths.append((rel_path, src_size, dst_size, False))
					else:
						rel_paths.append((rel_path, src_size, dst_size, True))
				self._logger.info(self._labels.size_check_finished)
				if hash_thread.is_alive():	# wait untill hashing has finished
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
				with (
					destination.joinpath(self._config.tsv_name).timed().open(mode='w', encoding='utf-8') as dst_fh,
					self._logger.get_remote_parent().joinpath(self._config.tsv_name).timed().open(mode='w', encoding='utf-8') as log_fh
				):
					print(self._labels.tsv_head, file=dst_fh)
					print(self._labels.tsv_head, file=log_fh)
					for (path, src_size, dst_size, okay), hash in zip(rel_paths, hash_thread.get_hashes()):
						line = '\t'.join((
							f'{path}',
							f'{src_size.readable()}',
							f'{src_size}',
							f'{dst_size if dst_size != None else "#####"}',
							f'{self._labels.okay if okay else self._labels.bad_size}',
							f'{hash}'
						))
						print(line, file=dst_fh)
						print(line, file=log_fh)
			except:
				self._error()
				continue
			if missing_paths:
				self._error(self._labels.error_missing.replace('#', f'{missing_paths}'))
			if bad_paths:
				self._error(self._labels.error_sizes.replace('#', f'{bad_paths}'))
			time_delta = perf_counter() - start_time
			self._logger.info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=time_delta)}'))
			if self._settings.trigger:
				try:
					destination.write_text_file(self._config.trigger_name, self._id)
				except:
					self._error()
			if self._settings.qualicheck:
				try:
					destination.write_text_file(self._config.qualicheck_name, self._id)
				except:
					self._error()
			if self._settings.sendmail and self._mail_address:
				try:
					JsonMail(self._config.mail_templet_path).send(
						self._config.mail_path.joinpath(self._config.mail_name).timed(fmt=f'%s_%t_{self._logger.login}%x'),
						self._settings.user,
						f'{source}',
						(f'{source}', source.total_bytes.readable(), f'{source.total_files}', f'{missing_paths}', f'{bad_paths}')
					)
				except:
					self._error()
			try:
				self._logger.close_remote()
			except:
				self._logger.warning()
		try:
			self._logger.close_user()
		except:
			self._logger.warning()
		return self.errors
