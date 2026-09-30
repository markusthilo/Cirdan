#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import strftime

class ToDo:
	'''Info what to do after import/upload'''

	def __init__(self, key, settings, config):
		'''Create object based on Config'''
		self.key = key
		if self.key:
			todo_dict = config.todo[config.destinations[settings.destination]['todo']][self.key]
			self.trigger_name = todo_dict['trigger_name']
			self.meta_name = todo_dict['meta_name']
			self.meta_content = todo_dict['meta_content']
		else:
			self.trigger_name = None
			self.meta_name = None
			self.meta_content = None

	def __repr__(self):
		'''Printable = key'''
		return self.key

	def write_meta(self, dir_path):
		'''Write meta file if given'''
		if self.meta_name:
			dir_path.write_text_file(strftime(self.meta_name), self.meta_content)

	def write_trigger(self, dir_path, id):
		'''Write trigger file if given'''
		if self.trigger_name:
			dir_path.write_text_file(self.trigger_name, id)