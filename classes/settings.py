#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load, dump

class Settings:
	'''Handle user settings'''

	def __init__(self, config):
		'''Generate object for setting, try to load from JSON file'''
		self._path = config.local_path / config.settings_name
		self._keys = ('destination', 'sendmail', 'user', 'mail_subject')
		try:
			with self._path.open(encoding='utf-8') as fp:
				items = load(fp)
		except:
			items = dict()
			config.local_path.mkdir(parents=True, exist_ok=True)
		self.destination = items['destination'] if 'destination' in items and items['destination'] else ''
		self.sendmail = items['sendmail'] if 'sendmail' in items else False
		self.user = items['user'] if 'user' in items else ''
		self.mail_subject = items['mail_subject'] if 'mail_subject' in items else config.mail['Default-Subject']

	def save(self):
		'''Save config file'''
		with self._path.open('w', encoding='utf-8') as fp:
			dump({key: self.__dict__[key] for key in self._keys}, fp)