#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from json import load as jload
from time import strftime

class JsonMail:
	'''Send mail'''

	BASE = {
		'mail': {'version_hr': 'v1.0', 'version': 100, 'meta': 'v1.0'},
  		'mail_meta': {'val_id': '0001', 'uuid': 'd8657443-d42a-4158-9898-7fe677c8e3d1'},
		'mail_content': {
			'From':				'MSD-Netz-Support@polizei.berlin.de',
			'FromDisplayName':	'MSD Netz Support',
			'FromPersonalNr':	'24521844',
			'ReplyTo':			'MSD-Netz-Support@polizei.berlin.de',
		}
	}
		#	"To":"Sam.Joachim@polizei.berlin.de",
		#	"Cc":"Markus.Thilo@polizei.berlin.de",
		#	"Subject":"MSD-Netz | Test-Email | Kopierprozess","Body":"Test-hier könnte auch ein HTM-Body stehen..."

	def __init__(self, config):
		''''''
		self._path = Path(config.mail)

	def send(self):
		'''Write mail to path from config'''
		mail = self.MAIL
		mail['To'] = f'to'
		mail['Subject'] = f'subject'
		mail['Body'] = f'body'
		try:
			with self._path.open('w') as fp:
				dump(mail, fp)
