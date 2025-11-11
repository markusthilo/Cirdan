#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load

class Json:
	'''JSOM file to Object'''

	def __init__(self, path):
		'''Read JSON file an buld object'''
		with path.open(encoding='utf-8') as fp:
			for key, value in load(fp).items():
				self.__dict__[key] = value
