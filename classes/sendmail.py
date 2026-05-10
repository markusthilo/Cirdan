#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from email.message import EmailMessage
from smtplib import SMTP


class SendMail:
	'''Send mail via SMTP without authentication (open relay / internal server).'''

	def __init__(self, mail_config):
		'''Read JSON file as base for the mail'''
		self._host = mail_config['smtp_host']
		self._port = mail_config['smtp_port']
		self._timeout = mail_config['smtp_timeout']
		self._from = mail_config['From']
		self._reply_to = mail_config['Reply-To']
		self._subject = mail_config['Subject']
		self._body = mail_config['body']

	def send(self, to_address, source, inserts):
		'''Send prepared mail to an SMTP server (no LOGIN).'''
		msg = EmailMessage()
		msg['From'] = self._from
		msg['Reply-To'] = self._reply_to
		msg['To'] = to_address
		msg['Subject'] = self._subject.replace('%', source)
		body_parts = self._body.split('#', len(inserts))
		body = body_parts[0]
		for insert, part in zip(inserts, body_parts[1:]):
			body += f'{insert}{part}'
		msg.set_content(body)
		with SMTP(self._host, self._port, timeout=self._timeout) as smtp:
			smtp.send_message(msg)
