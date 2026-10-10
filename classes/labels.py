#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load

class Labels:
	"""Labels = language packet for Cirdan"""

	def __init__(self, config: Config, version: str) -> None:
		with path.open(encoding="utf-8") as fp:
			for key, value in load(fp).items():
				self.__dict__[key] = value
		self.version = version
