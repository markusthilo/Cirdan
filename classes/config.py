#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import executable as __executable__
from json import load
from platform import system
from classes.path import Path

__app_path__ = Path(__file__).parent.parent if Path(__executable__).name.startswith('python') else Path(__executable__).parent

class Config:
	'''Handle configuration file in JSON format'''

	def __init__(self, path=None):
		'''Read config file'''
		self.app_path = __app_path__
		self.system = system()
		path = path if path else self.app_path.joinpath('config.json')
		with path.open(encoding='utf-8') as fp:
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
