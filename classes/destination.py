#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from classes.regex import RegEx
from json import load

class Destination:
	'''Destination class'''

	def __init__(self, path, whitelist=None, countlist=None, create_todo_name=None, username=None):
		'''Destination settings'''
		self._path = path
		self._create_todo_name = create_todo_name
		self._username = username
		self._whitelist = RegEx(whitelist) if whitelist else None
		self._countlist = RegEx(countlist) if countlist else None
		self.sub_dir_paths = list()
		self.counted_paths = {pattern: 0 for pattern in countlist} if countlist else dict()

	def __repr__(self):
		'''Printable destination'''
		return f'{self._path.parent.name}/{self._path.name}'

	def check(self):
		'''Check destination directory and return list of sub directories that might be triggered'''
		for sub_dir_path in self._path.iterdir():
			if sub_dir_path.is_dir():
				yield f'{self._path}/{sub_dir_path.name}'
				if self._whitelist:
					for white_path, white_relative in sub_dir_path.rrglob('*'):
						if self._whitelist.search(white_relative):
							self.sub_dir_paths.append(sub_dir_path)
							break
				else:
					self.sub_dir_paths.append(sub_dir_path)
				if self._create_todo_name:
					trigger_path = sub_dir_path.joinpath(self._create_todo_name)
					try:
						with trigger_path.open(encoding='utf-8') as fp:
							todo_dict = load(fp)
							if todo_dict['username'] != self._username:
								self.sub_dir_paths.pop()
					except:
						self.sub_dir_paths.pop()
		return self.sub_dir_paths

	def count_paths(self, sub_dir_path):
		'''Count paths for given RegEx patterns'''
		if self._countlist:
			for path, relative in self._path.joinpath(sub_dir_path.name).rrglob('*'):
				if pattern := self._countlist.search(relative):
					self.counted_paths[pattern] += 1
				yield relative
		else:
			yield ''
