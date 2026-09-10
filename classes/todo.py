#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.logger import Logger as Log

class ToDo:
	'''Info what to do after import/upload'''

	def __init__(self, key, settings, config):
		'''Create object based on Config'''
		self.key = key
		if self.key:
			self.value = config.metadata[config.destinations[settings.destination]['metadata']][self.key]
		else:
			self.value = None

	def __repr__(self):
		'''Printable = key'''
		return self.key

	def get(self):
		'''Return key and value'''
		return self.key, self.value
