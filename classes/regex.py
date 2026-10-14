#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import compile as re_compile, Pattern, error as ReError

class RegEx:
	"""Search by regular expressions"""

	def __init__(self, patterns: list[str] | tuple[str, ...] | str) -> None:
		if isinstance(patterns, str):
			patterns = (patterns,)
		compiled: list[Pattern[str]] = []
		for pattern in patterns:
			try:
				compiled.append(re_compile(pattern))
			except ReError as exc:
				raise ValueError(f"Invalid regular expression: {pattern!r}") from exc
		self._compiled = tuple(compiled)

	def get_patterns(self) -> tuple[str, ...]:
		"""Return the original pattern strings"""
		return tuple(regex.pattern for regex in self._compiled)

	def search(self, arg_str: str) -> str | None:
		"""Return first matching pattern string, or None"""
		for regex in self._compiled:
			if regex.search(arg_str):
				return regex.pattern
		return None

	def __repr__(self) -> str:
		return f"RegEx({list(self.get_patterns())!r})"
