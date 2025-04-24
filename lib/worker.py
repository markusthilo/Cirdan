#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from re import search, sub
from time import strftime, sleep, perf_counter
from datetime import timedelta

class Copy:
	'''Copy functionality'''

	### hard coded configuration ###
	LOGLEVEL = logging.INFO				# set log level
	LOG_NAME = 'log.txt' 				# log file name
	TSV_NAME = 'fertig.txt'				# file name for csv output textfile - file is generaten when all is done
	MAX_PATH_LEN = 230					# throw error when paths have more chars
	BLACKLIST_FILES = (					# prohibited at path depth 1
		'fertig.txt',
		'verarbeitet.txt',
		'fehler.txt',
		'start.txt',
		'zu_loeschen.txt'
	)
	BLACKLIST_PATHS = {					# forbidden paths
		'Help': ('HTML5', 'LicenseUpgrade')	# */Help/HTML5* && */Help/LicenseUpgrade*
	}
	TOPDIR_REG = r'^[0-9]{6}-([0-9]{4}|[0-9]{6})-[iSZ0-9][0-9]{5}$'	# how the top dir has to look

	@staticmethod
	def bad_destination():
		'''Check if target directory is reachable'''
		try:
			Copy.DST_PATH.iterdir()
		except FileNotFoundError:
			return (f'Zielverzeichnis {Copy.DST_PATH} ist nicht erreichbar')

	@staticmethod
	def matches_all(dir_path, patterns):
		'''Return True if all patterns are present under dir_path'''
		for pattern in patterns:
			if not dir_path.joinpath(pattern).exists():
				return False
		return True

	@staticmethod
	def bad_destination(root_path):
		'''Check if destination is clean'''
		if (Copy.DST_PATH / root_path.name / Copy.TSV_NAME).is_file():
			return f'{root_path} befindet sich bereits im Ziel- bzw. Importverzeichnis und wird weiterverarbeitet'

	@staticmethod
	def bad_source(root_path):
		'''Check if source directory is ok'''
		if not root_path.is_dir():
			return f'{root_path} ist kein Verzeichnis oder nicht erreichbar'
		if not search(Copy.TOPDIR_REG, root_path.name):
			return f'{root_path} hat nicht das korrekte Namensformat (POLIKS-Vorgansnummer)'
		for path in root_path.rglob('*'):
			if len(f'{path.absolute()}') > Copy.MAX_PATH_LEN:
				return f'Der Pfad {path.absolute()} hat mehr als {Copy.MAX_PATH_LEN} Zeichen'

	@staticmethod
	def blacklisted_paths(root_path):
		'''Check paths by blacklists'''
		for path in root_path.rglob('*'):
			if path.is_dir() and path.name in Copy.BLACKLIST_PATHS and Copy.matches_all(path, Copy.BLACKLIST_PATHS[path.name]):
				yield path, f'Das Verzeichnis {path} könnte gegen Pfad-/Dateikonventionen verstoßen!'
		yield None, None

	@staticmethod
	def blacklisted_files(root_path):
		for path in root_path.glob('*'):
			if path.is_file() and path.name in Copy.BLACKLIST_FILES:
				yield path, f'Eine Datei {path} darf sich nicht in {root_path} befinden!'
		yield None, None

	@staticmethod
	def _bytes(size, format_k='{iec} / {si}', format_b='{b} byte(s)'):
		'''Genereate readable size string,
			format_k: "{iec} / {si} / {b} bytes" gives e.g. 9.54 MiB / 10.0 MB / 10000000 bytes
			format_b will be returned if size < 5 bytes
		'''
		def _round(*base):	# intern function to calculate human readable
			for prefix, b in base:
				rnd = round(size/b, 2)
				if rnd >= 1:
					break
			if rnd >= 10:
				rnd = round(rnd, 1)
			if rnd >= 100:
				rnd = round(rnd)
			return f'{rnd} {prefix}', rnd
		try:	# start method here
			size = int(size)
		except (TypeError, ValueError):
			return 'undetected'
		iec = None
		rnd_iec = 0
		si = None
		rnd_si = 0
		if '{iec}' in format_k:
			iec, rnd_iec = _round(('PiB', 2**50), ('TiB', 2**40), ('GiB', 2**30), ('MiB', 2**20), ('kiB', 2**10))
		if '{si}' in format_k:
			si, rnd_si = _round(('PB', 10**15), ('TB', 10**12), ('GB', 10**9), ('MB', 10**6), ('kB', 10**3))
		if not '{b}' in format_k and rnd_iec == 0 and rnd_si == 0:
			return format_b.format(b=size)
		return format_k.format(iec=iec, si=si, b=size)

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

class Worker(Thread):
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
