#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from time import strftime, sleep, perf_counter
from datetime import timedelta
from threading import Thread
from lib.robocopy import RoboCopy
from lib.size import Size

class Worker:
	'''Main functionality'''

	def __init__(self, src_paths, app_path, config, labels, log=None, trigger=True, kill=None, echo=print):
		'''Do the work'''
		self._echo = echo
		self.error = True
		robocopy = RoboCopy()
		logger = logging.getLogger()
		logger.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
		local_log_path = log if log else app_path / 'log.txt'
		local_log_fh = logging.FileHandler(mode='w', filename=local_log_path)
		local_log_fh.setFormatter(formatter)
		logger.addHandler(local_log_fh)
		for src_path in src_paths:
			remote_log_fh = logging.FileHandler(
				mode = 'w',
				filename = Path(config.log, src_path.name, f'{strftime("%y%m%d-%H%M")}-log.txt')
			)
			remote_log_fh.setFormatter(formatter)
			logger.addHandler(remote_log_fh)
			logging.info(f'{config.user}@{config.domain}, {config.group}')
			start_time = perf_counter()
			self._info(f'{labels.reading_structure} {src_path}')
			src_file_paths = list()
			src_file_sizes = list()
			total_bytes = 0
			try:
				for path in src_path.rglob('*'):	# analyze root structure
					if path.is_file():
						size = path.stat().st_size
						src_file_paths.append(path)
						src_file_sizes.append(size)
						total_bytes += size
			except Exception as ex:
				self._error(ex)
			dst_path = Path(config.target, src_path.name)
			self._info(f'{labels.starting_robocopy}: {src_path} -> {dst_path}, {Size(total_bytes).readable()}')
			return
			try:
				hash_thread = HashThread(src_file_paths)
				echo(f'Starte Berechnung von {len(self.src_file_paths)} MD5-Hashes')
				hash_thread.start()
			except Exception as ex:
				msg = f'Konnte Thread, der Hash-Werte bilden soll, nicht starten:\n{ex}'
				logging.error(msg)
				echo(f'FEHLER: {msg}')
		for line in robocopy.copy_dir(self.root_path, self.dst_path):
			if line.endswith('%'):
				self.echo(line, end='\r')
			else:
				self.echo(line)
		if robocopy.returncode > 5:
			msg = f'"{robocopy}" hatte ein Problem, Rückgabewert: {robocopy.returncode}'
			logging.error(msg)
			raise ChildProcessError(ex)
		msg = f'"{robocopy}" wurde beendet, starte Überprüfung anhand Dateigröße'
		logging.info(msg)
		echo(msg)
		errors = 0
		mismatches = 0
		total = len(self.src_file_paths)
		for cnt, (src_path, src_size) in enumerate(zip(self.src_file_paths, self.src_file_sizes), start=1):
			echo(f'{int(100*cnt/total)}%', end='\r')
			dst_path = self.dst_path.joinpath(src_path.relative_to(self.root_path))
			try:
				dst_size = dst_path.stat().st_size
			except Exception as ex:
				msg = f'Dateigröße von {dst_path} konnte nicht ermittelt werden:\n{ex}'
				logging.warning(msg)
				echo(f'WARNING: {msg}')
				errors += 1
			else:
				if dst_size != src_size:
					msg = f'Dateigrößenabweichung: {src_path} => {src_size}, {dst_path} => {dst_size}'
					logging.warning(msg)
					echo(f'WARNING: {msg}')
					mismatches += 1
		msg = 'Überprüfung anhand Dateigröße ist abgeschlossen'
		logging.info(msg)
		echo(msg)
		if hash_thread.is_alive():
			msg = 'Führe die Hash-Wert-Berechnung fort'
			logging.info(msg)
			echo(msg)
			index = 0
			while hash_thread.is_alive():
				echo(f'{"|/-\\"[index]}  ', end='\r')
				index += 1
				if index > 3:
					index = 0
				sleep(.25)
			echo('MD5-Hashes-Berechnung ist abgeschlossen')
		hash_thread.join()
		tsv = 'Pfad\tMD5-Hash'
		for path, md5 in hash_thread.get_hashes():
			tsv += f'\n{path.relative_to(self.root_path.parent)}\t{md5}'
		log_tsv_path = log_dir_path / f'{strftime('%y%m%d-%H%M')}-{self.TSV_NAME}'
		try:
			log_tsv_path.write_text(tsv, encoding='utf-8')
		except Exception as ex:
			msg = f'Konnte Log-Datei {log_tsv_path} nicht erzeugen:\n{ex}'
			logging.error(msg)
			raise OSError(ex)
		if errors:
			msg = f'Die Größe von {errors} Datei(en) konnte nicht ermittelt werden'
			logging.error(msg)
			if not mismatches:
				raise OSError(msg)
			echo(f'WARNING: {msg}')
		if mismatches:
			msg = f'Bei {mismatches} Datei(en) stimmt die Größe der Zieldatei nicht mit der Ausgangsdatei überein'
			logging.error(msg)
			raise RuntimeError(msg)
		if trigger:
			dst_tsv_path = self.dst_path / self.TSV_NAME
			try:
				dst_tsv_path.write_text(tsv, encoding='utf-8')
			except Exception as ex:
				msg = f'Konnte {dst_tsv_path} nicht erzeugen:\n{ex}'
				logging.error(msg)
				echo(msg)
				raise OSError(ex)
			


		end_time = perf_counter()
		delta = end_time - start_time
		msg = f'Fertig - das Kopieren dauerte {timedelta(seconds=delta)} (Stunden, Minuten, Sekunden)'
		logging.info(msg)
		echo(msg)
		logging.shutdown()

	def _info(self, msg):
		'''Log info and echo message'''
		logging.info(msg)
		self._echo(msg)

	def _error(self, ex):
		'''Log error and raise exception'''
		msg = f'{type(ex)}: {ex}'
		logging.error(msg)
		self._echo(msg)
		raise ex