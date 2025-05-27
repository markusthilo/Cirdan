#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from json import load, dump
from time import strftime

class JsonMail:
	'''Send mail'''

	def __init__(self, file_path):
		'''Read JSON file as base for the mail'''	
		with file_path.open() as fp:
			self._mail = {key: value for key, value in load(fp).items()}

	def send(self, dir_path, to='markus.thilo@polizei.berlin.de', id='TEST', tsv='TEST'):
		'''Write mail to directory observed by mail daemon'''
		mail = self._mail.copy()
		mail['mail_content']['To'] = to
		mail['mail_content']['Subject'] = mail['mail_content']['Subject'].replace('#', id)
		mail['mail_content']['Body'] = mail['mail_content']['Body'] + tsv
		with dir_path.joinpath(
			f'{strftime("%y%m%d_%H%M%S")}_{mail['mail_content']["To"].split('@')[0].replace('.', '_')}.json'
		).open('w') as fp:
			dump(mail, fp)
