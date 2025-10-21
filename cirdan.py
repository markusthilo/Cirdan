#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.9.3_2025-10-21'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Copy to import folder and generate trigger files'

from sys import executable as __executable__
from sys import exit as sys_exit
from argparse import ArgumentParser
from pathlib import Path
from classes.config import Config
from classes.settings import Settings
from classes.checker import Checker
from classes.worker import Worker
from classes.gui import Gui

__parent_path__ = Path(__file__).parent if Path(__executable__).name == 'python.exe' else Path(__executable__).parent

if __name__ == '__main__':  # start here when run as application
	argparser = ArgumentParser(prog=f'Cirdan Version {__version__}', description='Custom upload/copy tool using RoboCopy')
	argparser.add_argument('-d', '--done', action='store_true',
		help='Trigger processing software to send e-mail to user when finished')
	argparser.add_argument('-g', '--gui', action='store_true',
		help='Use GUI with given root directory as command line parameters')
	argparser.add_argument('-l', '--log', type=str, metavar='FILE',
		help='File to store log (default: log.txt in app folder)')
	argparser.add_argument('-m', '--nomail', action='store_true',
		help='Do not send e-mail to user when copy process has finished')
	argparser.add_argument('-n', '--notrigger', action='store_true',
		help='Do not triggedr further process to handle/move uploaded data')
	argparser.add_argument('source', nargs='?', help='Source directory', type=str, metavar='DIRECTORY')
	args = argparser.parse_args()
	log_path = Path(args.log.strip('"')) if args.log else None
	source_path = Path(args.source.strip('"')) if args.source else None
	config = Config(__parent_path__ / 'config.json')
	labels = Config(__parent_path__ / 'labels.json')
	settings = Settings(__parent_path__ / 'settings.json', config)
	if args.done:
		settings.done = True
	if args.nomail:
		settings.finished = False
	if args.notrigger:
		settings.triggert = False
	if args.source and not args.gui:	# run in terminal
		check = Checker(config)
		check.source(source_path)
		check.destination(Path(config.target, config.destinations[settings.destination], source_path.name))
		if not settings.user:
			raise ValueError('User name has not been set')
		Worker(__parent_path__, config, settings, labels, log=log_path).copy_dir(source_path)
	else:	# open gui if no argument is given
		gui_defs = Config(__parent_path__ / 'gui.json')
		Gui(source_path, __parent_path__, config, labels, settings, gui_defs, __version__, log_path).mainloop()
	sys_exit()