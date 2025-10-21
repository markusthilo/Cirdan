#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.config import Config

class Settings(Config):
	'''Handle user settings'''

	def __init__(self, path, config):
		'''Generate object for setting, try to load from JSON file'''
		super().__init__(path)
		if not self.exists('user'):
			self.create('user', '')
		if not self.exists('destination'):
			self.create('destination', config.default_destination)
		if not self.exists('trigger'):
			self.create('trigger', True)
		if not self.exists('finished'):
			self.create('finished', True)
		if not self.exists('done'):
			self.create('done', False)
