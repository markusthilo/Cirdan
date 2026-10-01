#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import strftime

class ToDo:
	'''Info what to do after import/upload'''

	def __init__(self, key, settings, config):
		'''Create object based on Config'''
		self.key = key
		self.create_todo_name = config.create_todo_name
		if self.key:
			try:
				todo_dict = config.todo[config.destinations[settings.destination]['todo']][self.key]
			except KeyError:
				pass
			else:
				self.trigger_name = todo_dict['trigger_name']
				self.meta_name = todo_dict['meta_name']
				self.meta_content = todo_dict['meta_content']
				self.delete_name = todo_dict['delete_name']
				return
		self.trigger_name = None
		self.meta_name = None
		self.meta_content = None
		self.delete_name = None

	def __repr__(self):
		'''Printable = key'''
		return self.key

	def delete_trigger(self, dir_path):
		'''Delete trigger file if given'''
		if self.delete_name:
			dir_path.joinpath(self.delete_name).unlink(missing_ok=True)

	def write_meta(self, dir_path, counted_paths):
		'''Write meta file if given'''
		if self.meta_name:
			if '%p' in self.meta_content:
				json = '{\n'
				for pattern, n in counted_paths.items():
					json += f'        {{"pattern": "{pattern}", "matches": {n}}}\n'
				json += '    }'
				content = self.meta_content.replace('%p', json)
			else:
				content = self.meta_content
			dir_path.write_text_file(self.meta_name, content, use_strftime=True)

	def write_trigger(self, dir_path, id):
		'''Write trigger file if given'''
		if self.trigger_name:
			dir_path.write_text_file(self.trigger_name, id)
