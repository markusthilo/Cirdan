#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load, dump
from getpass import getuser

class Settings:
	'''Handle user settings'''

	def __init__(self, config, username=None):
		'''Generate object for setting, try to load from JSON file'''
		self._path = config.local_path / config.settings_name
		self._keys = ('username', 'destination', 'sendmail', 'mail_to', 'mail_subject')
		try:
			with self._path.open(encoding='utf-8') as fp:
				items = load(fp)
		except:
			items = dict()
			config.local_path.mkdir(parents=True, exist_ok=True)
		self.username = username if username else items['username'] if 'username' in items and items['username'] else getuser()
		self.destination = items['destination'] if 'destination' in items and items['destination'] else ''
		self.sendmail = items['sendmail'] if 'sendmail' in items else False
		self.mail_to = items['mail_to'] if 'mail_to' in items else ''
		self.mail_subject = items['mail_subject'] if 'mail_subject' in items else config.mail['Default-Subject']

	def save(self):
		'''Save settings file'''
		with self._path.open('w', encoding='utf-8') as fp:
			dump({key: self.__dict__[key] for key in self._keys}, fp)