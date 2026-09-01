#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPException


class SendMail:
	'''Send mail via SMTP without authentication (open relay / internal server)'''

	def __init__(self, mail_config):
		'''Build object based on mail section of config file'''
		self._host = mail_config['smtp_host']
		self._port = mail_config['smtp_port']
		self._timeout = mail_config['smtp_timeout']
		self._from = mail_config['From']
		self._reply_to = mail_config['Reply-To']
		self._body = mail_config['body']

	def is_reachable(self):
		'''Return True if the configured SMTP host accepts a connection.'''
		try:
			with SMTP(self._host, self._port, timeout=self._timeout):
				pass
			return True
		except (OSError, SMTPException):
			return False

	def send(self, to_address, subject, inserts):
		'''Compose and send mail to SMTP server '''
		body_parts = self._body.split('%', len(inserts))
		body = body_parts[0]
		for insert, part in zip(inserts, body_parts[1:]):
			body += f'{insert}{part}'
		msg = MIMEText(body, 'plain', 'utf-8')
		msg['From'] = self._from
		msg['Reply-To'] = self._reply_to
		msg['To'] = to_address
		msg['Subject'] = subject
		with SMTP(self._host, self._port, timeout=self._timeout) as smtp:
			smtp.send_message(msg)
