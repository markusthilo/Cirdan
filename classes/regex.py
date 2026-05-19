#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from re import compile as re_compile

class RegEx:
	'''Search by regular expressions'''

	def __init__(self, patterns):
		'''Compile regular expressions'''
		self._compiled = tuple(re_compile(pattern) for pattern in patterns)

	def search(self, arg_str):
		'''Return first string that matches any pattern and the matching pattern'''
		for regex in self._compiled:
			if regex.search(arg_str):
				return regex.pattern
		return None
