#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.9.5_2025-10-30'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Copy to import folder and generate trigger files'

from sys import executable as __executable__
from sys import exit as sys_exit
from argparse import ArgumentParser
from pathlib import Path
from classes.jsonobject import JsonObject
from classes.config import Config
from classes.settings import Settings
from classes.pathhandler import PathHandler
from classes.worker import Worker
from classes.gui import Gui

__parent_path__ = Path(__file__).parent if Path(__executable__).name == 'python.exe' else Path(__executable__).parent

if __name__ == '__main__':  # start here when run as application
	argparser = ArgumentParser(prog=f'Cirdan Version {__version__}', description='Custom upload/copy tool using RoboCopy')
	argparser.add_argument('-d', '--destination', type=str, metavar='STRING',
		help='Destination to copy to')
	argparser.add_argument('-g', '--gui', action='store_true',
		help='Use GUI with given root directory as command line parameters')
	argparser.add_argument('-l', '--log', type=str, metavar='FILE',
		help='File to store log')
	argparser.add_argument('-n', '--notrigger', action='store_true',
		help='Do not triggedr further process to handle/move uploaded data')
	argparser.add_argument('-q', '--qualicheck', action='store_true',
		help='Trigger qualicheck when the entire process has finished')
	argparser.add_argument('-s', '--sendmail', action='store_true',
		help='Send e-mail to user when copy process has finished')
	argparser.add_argument('-u', '--user', type=str, metavar='USERNAME',
		help='Username / e-mail-address without domain (e.g. john.doe)')
	argparser.add_argument('source', nargs='?', help='Source directory', type=str, metavar='DIRECTORY')
	args = argparser.parse_args()
	config = Config(__parent_path__)
	labels = JsonObject(__parent_path__ / 'labels.json')
	labels.version = __version__
	settings = Settings(config)
	if args.destination:
		settings.destination = args.destination
	log_path = Path(args.log.strip('"\'')) if args.log else None
	settings.trigger = not args.notrigger
	if args.user:
		settings.user = args.user.strip('"\'')
	source_path = Path(args.source.strip('"\'')) if args.source else None
	if source_path:
		ph = PathHandler(config, labels)
		if not ph.is_accessable_dir(config.log_path):
			raise PermissionError(labels.bad_log_dir.replace('#', f'{config.log_path}'))
		if not ph.is_accessable_dir(config.mail_path):
			raise PermissionError(labels.bad_mail_dir.replace('#', f'{config.mail_path}'))
		ph.check_source_path(source_path)
		if not args.gui:	# run in terminal
			settings.qualicheck = args.qualicheck
			settings.sendmail = args.sendmail
			Worker(__parent_path__, config, labels, settings, local_log=log_path).copy_dir(source_path)
			sys_exit()
	Gui(__parent_path__, config, labels, settings, log=log_path, source=source_path).mainloop()
	sys_exit()
