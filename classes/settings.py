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
		self._keys = ('destination', 'qualicheck', 'sendmail', 'trigger', 'user')
		self.__dict__['destination'] = items['destination'] if 'destination' in items else config.default_destination
		self.__dict__['qualicheck'] = items['qualicheck'] if 'qualicheck' in items else False
		self.__dict__['sendmail'] = items['sendmail'] if 'sendmail' in items else True
		self.__dict__['trigger'] = items['trigger'] if 'trigger' in items else True
		self.__dict__['user'] = items['user'] if 'user' in items else ''

	def save(self):
		'''Save config file'''
		with self._path.open('w', encoding='utf-8') as fp:
			dump({key: self.__dict__[key] for key in self._keys}, fp)