#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from time import strftime, sleep, perf_counter
from datetime import timedelta
from threading import Thread
from lib.size import Size

class Copy:
	'''Copy functionality'''

	def __init__(self, root_path, trigger=True, robocopy=None, echo=print, check_paths=True):
		'''Generate object to copy and to zip'''
		self.root_path = root_path.resolve()
		robocopy = robocopy if robocopy else RoboCopy()
		self.echo = echo
		if ex := self.bad_destination(self.root_path):
			raise ValueError(ex)
		if ex := self.bad_source(self.root_path):
			raise ValueError(ex)
		for path, msg in self.blacklisted_files(self.root_path):
			if not path:
				break
			if echo == print:
				if input(f'\n{msg}\nDatei löschen oder Abbrechen ("löschen" oder beliebige andere Eingabe): ').lower() == 'löschen':
					try:
						path.unlink()
					except Exception as ex:
						echo(f'Konnte Datei {path} nicht löschen:\n{ex}')
						raise OSError(ex)
					echo(f'Die Datei {path} wurde auf Wunsch des Anwenders gelöscht')
				else:
					return
			else:
				raise ValueError(msg)
		if check_paths:
			for path, msg in self.blacklisted_paths(self.root_path):
				if not path:
					break
				if echo == print:
					answer = input(f'\n{msg}\nVerzeichnis löschen, trotzdem Kopieren oder Abbrechen ("löschen", "kopieren" oder beliebige andere Eingabe): ').lower()
					if answer == 'löschen':
						try:
							rmtree(path)
						except Exception as ex:
							echo(f'Konnte Verzeichnis {path} nicht löschen:\n{ex}')
							raise OSError(ex)
						echo(f'Das Verzeichnis {path} wurde auf Wunsch des Anwenders gelöscht')
					elif answer == 'kopieren':
						continue
					else:
						return
				else:
					raise ValueError(msg)
		self.dst_path = self.DST_PATH / self.root_path.name
		try:
			self.dst_path.mkdir(exist_ok=True)
		except Exception as ex:
			echo(f'Kann das Zielverzeichnis {self.dst_path} nicht erstellen:\n{ex}')
			raise OSError(ex)
		log_dir_path = self.LOG_PATH / self.root_path.name
		try:
			log_dir_path.mkdir(exist_ok=True)
		except Exception as ex:
			echo(f'Kann das Log-Verzeichnis {log_dir_path} nicht erstellen:\n{ex}')
			raise OSError(ex)
		self.log_path = log_dir_path / f'{strftime('%y%m%d-%H%M')}-{self.LOG_NAME}'
		try:
			logging.basicConfig(	# start logging
				level = self.LOGLEVEL,
				filename = self.log_path,
				format = '%(asctime)s %(levelname)s: %(message)s',
				datefmt = '%Y-%m-%d %H:%M:%S'
			)
		except Exception as ex:
			echo(f'Kann das Loggen in die Datei {log_path} nicht starten:\n{ex}')
			raise RuntimeError(ex)
		start_time = perf_counter()
		msg = f'Lese Verzeichnisstruktur von {self.root_path}'
		logging.info(msg)
		echo(msg)
		self.src_file_paths = list()
		self.src_file_sizes = list()
		self.total_bytes = 0
		try:
			for path in self.root_path.rglob('*'):	# analyze root structure
				if path.is_file():
					size = path.stat().st_size
					self.src_file_paths.append(path)
					self.src_file_sizes.append(size)
					self.total_bytes += size
		except Exception as ex:
			logging.error(ex)
			raise RuntimeError(ex)
		msg = f'Starte das Kopieren von {self.root_path} nach {self.dst_path}, {self._bytes(self.total_bytes)}'
		logging.info(msg)
		echo(msg)
		try:
			hash_thread = HashThread(self.src_file_paths)
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

class Worker:
	'''Main functionality'''

	def __init__(self, source_paths, config, log_dir=None, trigger=False):
		if work.log:
			log.write_text(work.log_path.read_text(encoding='utf-8'), encoding='utf-8')

class WorkThread(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Get all attributes from GUI and run Copy'''
		super().__init__()
		self.gui = gui
		self.errors = False
		self.log = ''

	def run(self):
		'''Run thread'''
		robocopy = RoboCopy()
		for source_path in self.gui.source_paths:
			try:
				copy = Copy(source_path,
					trigger = self.gui.generate_trigger.get(),
					robocopy = robocopy,
					echo = self.gui.echo,
					check_paths = self.gui.check_paths
				)
				if self.gui.write_log:
					self.log += f'### POLIKS-NR/Verzeichnis: {source_path.name} ###\nProtokoll:\n{copy.log_path.read_text()}'
			except Exception as ex:
				self.gui.echo(f'FEHLER: {ex}')
				self.errors = True
		self.gui.finished(self.errors, self.log)
