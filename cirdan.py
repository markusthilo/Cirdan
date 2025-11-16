#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.9.9_2025-11-16'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Custom upload/copy tool using RoboCopy'

from sys import executable as __executable__
from sys import exit as sys_exit
from os import getlogin
from argparse import ArgumentParser
from pathlib import Path
from classes.json import Json
from classes.config import Config
from classes.settings import Settings
from classes.logger import Logger
from classes.pathhandler import PathHandler
from classes.worker import Worker
from classes.gui import Gui

__parent_path__ = Path(__file__).parent if Path(__executable__).name == 'python.exe' else Path(__executable__).parent

if __name__ == '__main__':  # start here when run as application
	labels = Json(__parent_path__ / 'labels.json')
	labels.version = __version__
	labels.user = getlogin()
	argparser = ArgumentParser(prog=f'{labels.title} v{labels.version}', description=__description__)
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
	settings = Settings(config)
	if args.destination:
		settings.destination = args.destination
	log_path = Path(args.log.strip('"\'')) if args.log else None
	settings.trigger = not args.notrigger
	if args.user:
		settings.user = args.user.strip('"\'')
	source_path = Path(args.source.strip('"\'')) if args.source else None
	if not source_path or args.gui:
		Gui(__parent_path__, config, labels, settings, logger=logger, user_log=log_path, source=source_path).mainloop()
		sys_exit()
	logger = Logger(config, labels)
	logger.add_lastlog()
	try:
		if not source_path:
			raise FileNotFoundError(labels.missing_source_dir)
		ph = PathHandler(config, labels)
		if not ph.is_accessable_dir(config.log_path):
			raise PermissionError(labels.bad_log_dir.replace('#', f'{config.log_path}'))
		if not ph.is_accessable_dir(config.mail_path):
			raise PermissionError(labels.bad_mail_dir.replace('#', f'{config.mail_path}'))
		ph.check_source_path(source_path)
		settings.qualicheck = args.qualicheck
		settings.sendmail = args.sendmail
		Worker(__parent_path__, config, labels, settings, logger=logger, user_log=log_path).copy_dir(source_path)
	except Exception as ex:
		logging.error(f'{type(ex).__name__}: {ex}')
		raise ex
	sys_exit()
