#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep, perf_counter
from datetime import timedelta
from classes.logger import Logger as Log
from classes.path import Path
from classes.hash import HashThread
from classes.regex import RegEx
from classes.sendmail import SendMail 

class Worker:
	'''Main functionality'''

	def __init__(self, sources, config, labels, settings, robocopy, logger, user_log=None, kill=None, echo=print):
		'''Prepare copy process'''
		self._sources = sources
		self._config = config
		self._labels = labels
		self._settings = settings
		self._robocopy = robocopy
		self._logger = logger
		self._user_log = user_log
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.user}@{self._config.domain}' if self._settings.user else None
		self._id = f'{self._labels.username}: {self._logger.login}\n{self._labels.hostname}: {self._logger.node}'
		self.errors = list()

	def _error(self, message=None):
		'''Handle error'''
		self.errors.append(Log.error(message=message))

	def run(self):
		'''Start copy process'''
		start_time = perf_counter()
		if not self._sources:
			self._error(self._labels.no_sources)
			return self.errors
		destination_root_path = self._config.target_path.joinpath(self._config.destinations[self._settings.destination])
		if not destination_root_path.is_accessable_dir():
			self._error(self._labels.bad_destination.replace('#', f'{destination_root_path}'))
			return self.errors
		if self._user_log:	# start additional log if selected
			self._logger.add_user(self._user_log)
		for source in self._sources:	# check destination and create subdirs if necessary
			Log.info(self._labels.checking_source.replace('#', f'{source}'))
			for path, bad in source.check():
				if self._kill_switch and self._kill_switch.is_set():
					return
				self._echo(f'{path}', end='\r')
				if isinstance(bad, int):
					self._error(self._gui.labels.path_too_long.replace(
					'#1', f'{path}').replace(
					'#2', f'{bad}').replace(
					'#3', f'{self._gui.config.max_path_length}')
				)
					return self.errors
				if isinstance(bad, str):
					self._error(self._gui.labels.blacklisted.replace('#1', f'{path}').replace('#2', f'{bad}'))
					return self.errors
			Log.info(self._labels.found_files_in_source.replace(
				'#1', f'{len(source.files)}').replace(
				'#2', f'{source.path}').replace(
				'#3', f'{source.size.readable()}')
			)
			dst_path = Path(destination_root_path / source.name)
			try:	# create new destination directory if not already there
				dst_is_new = dst_path.mk()
			except:
				self._error()
				continue
			if dst_is_new:
				Log.info(self._labels.created_destination.replace('#', dst_path.name))
			elif self._config.destination_blacklist:	# check for blacklisted files in destination
				Log.info(self._labels.checking_destination.replace('#', f'{dst_path}'))
				blacklist = RegEx(self._config.destination_blacklist)
				for path, relative in dst_path.rrglob('*'):
					if self._kill_switch and self._kill_switch.is_set():
						return
					self._echo(f'{path}', end='\r')
					if pattern := blacklist.search(relative):
						self._error(self._labels.destination_blocked_by.replace('#1', relative).replace('#2', f'{pattern}'))
						return self._errors
		for source in self._sources:	# copy sources one by one
			try:
				dst_path = Path(destination_root_path / source.name)
				Log.info(self._labels.starting_copy.replace('#', f'{source.path}'))
				if error := self._logger.add_remote(source.path, dst_path):	# add log for one source / one destination
					self._errors(error)
				hash_thread = HashThread(source.files, max_size=self._config.max_hash_size, kill=self._kill_switch)	# start hashing
				Log.info(self._labels.starting_hashing)
				hash_thread.start()
				Log.info(f'{self._labels.starting_robocopy}: {source} -> {dst_path}')
				for line in self._robocopy.copy_dir(source.path, dst_path):
					if line.endswith('%'):
						self._echo(line, end='\r')
					else:
						self._echo(line)
					if self._kill_switch and self._kill_switch.is_set():
						self._robocopy.terminate()
						return
				try:
					robocopy_msg = f'{self._robocopy.returncode} - ' + self._labels.__dict__[f'returncode_{self._robocopy.returncode}']
				except KeyError:
					robocopy_msg = f'{self._robocopy.returncode}'
				robocopy_msg = self._labels.robocopy_returned.replace('#', robocopy_msg)
				if self._robocopy.returncode > 5:
					Log.warning(robocopy_msg)
				else:
					Log.info(robocopy_msg)
				Log.info(self._labels.starting_size_check)	# start size check
				total_files = len(source.files)
				missing_paths = 0
				bad_paths = 0
				for cnt, fd in enumerate(source.files, start=1):
					self._echo(f'{int(100*cnt/total_files)}%', end='\r')
					relative = fd['relative']
					src_size = fd['size']
					dst_size = dst_path.parent.joinpath(relative).get_filesize()
					if dst_size is None:
						Log.warning(self._labels.missing_file.replace('#', relative))
						missing_paths += 1
						fd['dst_size'] = None
						fd['dst_ok'] = False
					elif dst_size != src_size:
						Log.warning(self._labels.mismatching_sizes.replace(
							'#1', relative).replace(
							'#2', f'{src_size}').replace(
							'#3', f'{dst_size}')
						)
						bad_paths += 1
						fd['dst_size'] = dst_size
						fd['dst_ok'] = False
					else:
						fd['dst_size'] = dst_size
						fd['dst_ok'] = True
				Log.info(self._labels.size_check_finished)
				if hash_thread.is_alive():	# wait untill hashing has finished
					Log.info(self._labels.hashing_in_progress)
					index = 0
					while hash_thread.is_alive():
						self._echo(f'{"|/-\\"[index]}  ', end='\r')
						index += 1
						if index > 3:
							index = 0
						sleep(.25)
				hash_thread.join()
				Log.info(self._labels.hashing_finished)
				dst_tsv_path = dst_path.joinpath(self._config.tsv_name).timed()	# write tsv files
				log_tsv_path = self._logger.get_remote_parent().joinpath(self._config.tsv_name).timed()
				Log.debug(f'Start writing TSV files: {dst_tsv_path}, {log_tsv_path}')
				with dst_tsv_path.open_w() as dst_fh, log_tsv_path.open_w() as log_fh:
					print(self._labels.tsv_head, file=dst_fh)
					print(self._labels.tsv_head, file=log_fh)
					for fd in source.files:
						if fd['dst_ok']:
							msg = self._labels.okay
						elif fd['dst_size']:
							msg =  self._labels.bad_size
						else:
							msg = self._labels.missing
						line = '\t'.join((
							fd['relative'],
							fd['size'].readable(),
							str(fd['size']),
							'#####' if fd['dst_size'] is None else str(fd['dst_size']),
							msg,
							fd['hash']
						))
						print(line, file=dst_fh)
						print(line, file=log_fh)
			except:	# error handling
				self._error()
				continue
			if missing_paths:
				self._error(self._labels.error_missing.replace('#', f'{missing_paths}'))
			if bad_paths:
				self._error(self._labels.error_sizes.replace('#', f'{bad_paths}'))
			time_delta = perf_counter() - start_time
			Log.info(self._labels.copy_finished.replace('#', f'{timedelta(seconds=time_delta)}'))
			if self._settings.trigger:
				try:
					dst_path.write_text_file(self._config.trigger_name, self._id)
				except:
					self._error()
			if self._settings.qualicheck:
				try:
					dst_path.write_text_file(self._config.qualicheck_name, self._id)
				except:
					self._error()
			if self._settings.sendmail and self._mail_address:	# send mail to user
				try:
					SendMail(self._config.mail).send(
						self._mail_address,
						f'{source}',
						(f'{source}', source.size.readable(), f'{len(source.files)}', f'{missing_paths}', f'{bad_paths}')
					)
				except:
					self._error()
			try:
				self._logger.close_remote()
			except:
				Log.warning()
		try:
			self._logger.close_user()
		except:
			Log.warning()
		return self.errors
