#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Mapping, Sequence
from email.header import Header
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPException

class SendMail:
	"""Send mail via SMTP without authentication (open relay / internal server)"""

	def __init__(self, mail_config: Mapping[str, object]) -> None:
		"""Build object from the mail section of the config file"""
		try:
			self._host = str(mail_config["smtp_host"])
			self._port = int(mail_config["smtp_port"])  # type: ignore[arg-type]
			self._timeout = float(mail_config["smtp_timeout"])  # type: ignore[arg-type]
			self._from = str(mail_config["From"])
			self._reply_to = str(mail_config["Reply-To"])
			self._body = str(mail_config["body"])
		except KeyError as exc:
			raise ValueError(f"Missing mail config key: {exc.args[0]}") from exc

	def is_reachable(self) -> bool:
		"""Return True if the configured SMTP host accepts a connection"""
		try:
			with SMTP(self._host, self._port, timeout=self._timeout) as smtp:
				smtp.noop()
			return True
		except (OSError, SMTPException):
			return False

	def format_body(self, inserts: Sequence[object]) -> str:
		"""Replace each % in the body template with the next insert"""
		placeholders = self._body.count("%")
		if len(inserts) < placeholders:
			raise ValueError(
				f"Mail body needs {placeholders} value(s), got {len(inserts)}"
			)
		body_parts = self._body.split("%", placeholders)
		body = body_parts[0]
		for insert, part in zip(inserts[:placeholders], body_parts[1:], strict=True):
			body += f"{insert}{part}"
		return body

	def send(self, to_address: str, subject: str, inserts: Sequence[object]) -> None:
		"""Compose and send mail via SMTP"""
		msg = MIMEText(self.format_body(inserts), "plain", "utf-8")
		msg["From"] = self._from
		msg["Reply-To"] = self._reply_to
		msg["To"] = to_address
		msg["Subject"] = Header(subject, "utf-8")
		with SMTP(self._host, self._port, timeout=self._timeout) as smtp:
			smtp.send_message(msg)
