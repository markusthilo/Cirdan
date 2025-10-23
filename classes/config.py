#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import load
from pathlib import Path

class Config:
	'''Handle configuration file in JSON format'''

	def __init__(self, app_path):
		'''Read config file'''
		with app_path.joinpath('config.json').open(encoding='utf-8') as fp:
			for key, value in load(fp).items():
				if key.endswith('_path'):
					if value.startswith('$HOME/') or value.startswith('$HOME\\'):
						self.__dict__[key] = Path().home().joinpath(value[6:]).resolve()
					elif value.startswith('$APP/') or value.startswith('$APP\\'):
						self.__dict__[key] = app_path.joinpath(value[5:]).resolve()
					else:
						self.__dict__[key] = Path(value).resolve()
