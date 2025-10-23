#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load, dump

class Settings:
	'''Handle user settings'''

	def __init__(self, config):
		'''Generate object for setting, try to load from JSON file'''
		self._path = config.local_path / 'settings.json'
		try:
			with self._path.open(encoding='utf-8') as fp:
				items = load(fp)
		except:
			items = dict()
		self._keys = ('user', 'destination', 'trigger', 'finished', 'done')
		self.__dict__['user'] = items['user'] if 'user' in items else ''
		self.__dict__['destination'] = items['destination'] if 'destination' in items else config.default_destination
		self.__dict__['trigger'] = items['trigger'] if 'trigger' in items else True
		self.__dict__['finished'] = items['finished'] if 'finished' in items else True
		self.__dict__['done'] = items['done'] if 'done' in items else False

	def save(self):
		'''Save config file'''
		with self._path.open('w', encoding='utf-8') as fp:
			dump({key: self.__dict__[key] for key in self._keys}, fp)