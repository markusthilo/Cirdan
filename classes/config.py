#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load
from platform import system
from classes.path import Path

class Config:
	'''Handle configuration file in JSON format'''

	def __init__(self, app_path=Path().cwd()):
		'''Read config file'''
		self.app_path = app_path
		self.system = system()
		with self.app_path.joinpath('config.json').open(encoding='utf-8') as fp:
			for key, value in load(fp).items():
				if key == 'paths':
					for path_key, path_value in value[self.system].items():
						if path_value.startswith('$HOME/') or path_value.startswith('$HOME\\'):
							self.__dict__[path_key] = Path().home().joinpath(path_value[6:]).resolve()
						elif path_value.startswith('$APP/') or path_value.startswith('$APP\\'):
							self.__dict__[path_key] = self.app_path.joinpath(path_value[5:]).resolve()
						else:
							self.__dict__[path_key] = Path(path_value).resolve()
				else:	
					self.__dict__[key] = value
