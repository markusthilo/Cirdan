#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from re import search, sub

class Checker:
	'''Check source and destination'''

	def __init__(self, config):
		'''Set up checker'''
		self._config = config

	def bad_source(root_path):
		'''Check if source directory is okay'''
		if not root_path.is_dir():
			return f'{root_path} ist kein Verzeichnis oder nicht erreichbar'
		if not search(Copy.TOPDIR_REG, root_path.name):
			return f'{root_path} hat nicht das korrekte Namensformat (POLIKS-Vorgansnummer)'
		for path in root_path.rglob('*'):
			if len(f'{path.absolute()}') > Copy.MAX_PATH_LEN:
				return f'Der Pfad {path.absolute()} hat mehr als {Copy.MAX_PATH_LEN} Zeichen'

	def matches_all(dir_path, patterns):
		'''Return True if all patterns are present under dir_path'''
		for pattern in patterns:
			if not dir_path.joinpath(pattern).exists():
				return False
		return True

	@staticmethod
	def bad_destination():
		'''Check if target directory is reachable'''
		try:
			Copy.DST_PATH.iterdir()
		except FileNotFoundError:
			return (f'Zielverzeichnis {Copy.DST_PATH} ist nicht erreichbar')



	@staticmethod
	def bad_destination(root_path):
		'''Check if destination is clean'''
		if (Copy.DST_PATH / root_path.name / Copy.TSV_NAME).is_file():
			return f'{root_path} befindet sich bereits im Ziel- bzw. Importverzeichnis und wird weiterverarbeitet'



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
