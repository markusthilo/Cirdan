#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import perf_counter
from datetime import timedelta
from classes.logger import Logger as Log
from classes.path import Path
from classes.copymd5 import CopyMD5
from classes.gimmicks import Rotator
from classes.regex import RegEx
from classes.sendmail import SendMail 

class Worker:
	'''Main functionality'''

	def __init__(self, sources, todo, config, labels, settings, logger,
		user_log = None,
		kill = None,
		echo = print
	):
		'''Prepare copy process'''
		self._sources = sources
		self._todo = todo
		self._config = config
		self._labels = labels
		self._settings = settings
		self._logger = logger
		self._user_log = user_log
		self._kill_switch = kill
		self._echo = echo
		self._mail_address = f'{self._settings.mail_to}@{self._config.domain}' if self._settings.mail_to else None
		self.errors = list()

	def _error(self, message=None):
		'''Handle error'''
		self.errors.append(Log.error(message=message))

	def run(self):
		'''Copy process'''
		start_time = perf_counter()
		if not self._sources:
			self._error(self._labels.no_sources)
			return self.errors
		try:
			destination_root_path = self._config.target_path.joinpath(
				self._config.destinations[self._settings.destination]['sub_path']
				)
		except:
			self._error(self._labels.bad_destination.replace('#', f'{self._settings.destination}'))
			return self.errors
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
					self._echo()
					self._error(self._labels.path_too_long.replace(
					'#1', f'{path}').replace(
					'#2', f'{bad}').replace(
					'#3', f'{self._config.max_path_length}')
				)
					return self.errors
				if isinstance(bad, str):
					self._echo()
					self._error(self._labels.blacklisted.replace('#1', f'{path}').replace('#2', f'{bad}'))
					return self.errors
			if source.whitelist and not source.whitelist_match:
				self._echo()
				self._error(self._labels.no_whitelist_match.replace('#', f'{source.path}'))
				return self.errors
			Log.info(self._labels.found_files_in_source.replace(
				'#1', f'{len(source.files)}').replace(
				'#2', f'{source.path}').replace(
				'#3', f'{source.size.readable()}')
			)
			destination_path = destination_root_path / source.name
			if self._config.destination_blacklist and destination_path.is_dir():	# check for blacklisted files in destination
				Log.info(self._labels.checking_destination.replace('#', f'{destination_path}'))
				blacklist = RegEx(self._config.destination_blacklist)
				for path in destination_path.rrglob('*'):
					if self._kill_switch and self._kill_switch.is_set():
						return
					if pattern := blacklist.search(path.name):
						self._error(self._labels.destination_blocked_by.replace('#1', path.name).replace('#2', f'{pattern}'))
						self._echo()
						return self.errors
		for source in self._sources:	# copy sources one by one
			destination_path = destination_root_path / source.name
			tsv = f'{self._labels.tsv_head}\n'
			if error := self._logger.add_remote(source.path, destination_path):	# add log for one source / one destination
				self._error(error)
			self._todo.delete_trigger(destination_path)
			copymd5 = CopyMD5(source.path, destination_path)
			Log.info(f'{self._labels.starting}: {copymd5}')
			for line in copymd5.stdout:
				self._echo(line)
				if line.startswith('"'):
					tsv += line
				if self._kill_switch and self._kill_switch.is_set():
					copymd5.terminate()
					return
					


					rotator = Rotator(echo=self._echo)
					while hash_thread.is_alive():
						if self._kill_switch and self._kill_switch.is_set():
							return
						rotator.inc()


				dst_tsv_path = dst_path.append_name(self._config.tsv_name, use_strftime=True)	# write tsv files
				log_tsv_path = self._logger.get_remote_parent().append_name(self._config.tsv_name, use_strftime=True)
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
			try:
				self._todo.write_meta(dst_path, counted_paths)
			except:
				self._error()
			try:
				self._todo.write_trigger(dst_path, self._logger.id)
			except:
				self._error()
			if self._settings.sendmail and self._mail_address:	# send mail to user
				try:
					SendMail(self._config.mail).send(
						self._mail_address,
						self._settings.mail_subject,
						(f'{source.name}', source.size.readable(), f'{len(source.files)}', f'{missing_paths}', f'{bad_paths}')
					)
				except:
					self._error(self._labels.mail_error.replace('#', f'{self._mail_address}'))
			try:
				self._logger.close_remote()
			except:
				Log.warning()
		try:
			self._logger.close_user()
		except:
			Log.warning()
		return self.errors
