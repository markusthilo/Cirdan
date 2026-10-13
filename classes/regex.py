#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import compile as re_compile

class RegEx:
	"""Search by regular expressions"""

	def __init__(self, patterns):
		self._compiled = tuple[re_compile](re_compile(pattern) for pattern in patterns)

	def get_patterns(self) -> tuple[str]:
		"""Return compiled patterns"""
		return tuple[str](regex.pattern for regex in self._compiled)

	def search(self, arg_str: str) -> str | None:
		"""Return first matching pattern"""
		for regex in self._compiled:
			if regex.search(arg_str):
				return regex.pattern
		return None
