#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load, dump
from time import strftime

class JsonMail:
	'''Send mail'''

	def __init__(self, template_path):
		'''Read JSON file as base for the mail'''
		with template_path.open(encoding='utf-8') as fp:
			self._mail = load(fp)

	def send(self, path, user, source, inserts):
		'''Write mail to directory observed by mail daemon'''
		mail = self._mail.copy()
		mail['mail_content']['To'] = mail['mail_content']['To'].replace('#', user)
		mail['mail_content']['Subject'] = mail['mail_content']['Subject'].replace('#', source)
		body_parts = mail['mail_content']['Body'].split('#', len(inserts))
		mail['mail_content']['Body'] = body_parts[0]
		for insert, part in zip(inserts, body_parts[1:]):
			mail['mail_content']['Body'] += f'{insert}{part}'
		with path.open('w', encoding='utf-8') as fp:
			dump(mail, fp)
