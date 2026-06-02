#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '1.3.3_2026-06-02'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@proton.me'
__status__ = 'Testing'
__description__ = 'Custom upload/copy tool using Robocopy'

from sys import executable as __executable__, exit
from traceback import format_exc
from argparse import ArgumentParser
from classes.path import Path
from classes.json import Json
from classes.config import Config
from classes.settings import Settings
from classes.logger import Logger
from classes.robocopy import RoboCopy
from classes.worker import Worker
from classes.gui import Gui

__parent_path__ = Path(__file__).parent if Path(__executable__).name.startswith('python') else Path(__executable__).parent

if __name__ == '__main__':  # start here when run as application
	argparser = ArgumentParser(description=__description__)
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
	argparser.add_argument('-s', '--sendmail', type=str, metavar='STRING',
		help='Send e-mail when copy process has finished, argument is address without domain (e.g. john.doe for john.doe@example.net)')
	argparser.add_argument('-t', '--tolerant', action='store_true',
		help='Ignore encounter of blacklisted paths')
	argparser.add_argument('-v', '--version', action='store_true',
		help='Print version number')
	argparser.add_argument('source', nargs='?', help='Source directory', type=Path, metavar='DIRECTORY')
	args = argparser.parse_args()
	if args.version:
		print(__version__)
		exit(0)
	try:	# handle startup error
		config = Config(__parent_path__)
		labels = Json(config.labels_path)
		labels.version = __version__
		logger = Logger(config, labels)
	except Exception as ex:
		if args.source and not args.gui:	# error on cli
			raise ex
		Gui.startup_error(f'{ex}\n\n{format_exc().strip()}')	# show error message in window
		exit(1)
	try:
		settings = Settings(config)
		if args.destination:
			settings.destination = args.destination
		source_path = Path(args.source.strip('"\'')).resolve() if args.source else None	# strip " or ' because of power shell bug
		settings.tolerant = args.tolerant
		config.reachable_dsts = tuple(
			dst for dst in config.destinations
			if config.target_path.joinpath(config.destinations[dst]).is_accessable_dir()
		)
		if not config.reachable_dsts:
			raise NotADirectoryError(f'Unable to find or reach subdirectories of {config.target_path}')
		if settings.destination and not settings.destination in config.reachable_dsts:
			settings.destination = None
		if not settings.destination and config.reachable_dsts:
			settings.destination = config.reachable_dsts[0]
		if not config.log_path.is_accessable_dir():
			raise NotADirectoryError(f'Unable to find or reach log directory {config.log_path}')
	except Exception as ex:
		msg = logger.crash(ex)
		if not args.source or args.gui:
			Gui.startup_error(msg)	# show error message in window
		exit(1)
	log_path = Path(args.log.strip('"\'')) if args.log else None
	settings.tolerant = args.tolerant
	if source_path and not args.gui:	# no gui
		settings.trigger = not args.notrigger
		settings.qualicheck = args.qualicheck
		if args.sendmail:
			settings.sendmail = True
			settings.user = args.sendmail.strip('"\'')
		if not settings.user:
			settings.sendmail = False
		if not config.log_path.is_accessable_dir():
			logger.crash(labels.bad_log_dir.replace('#', f'{config.log_path}'))
			exit(1)
		try:
			settings.save()
		except Exception as ex:
			logger.warning(ex)
		if not args.sendmail:
			settings.sendmail = False
		if Worker([source_path], config, labels, settings, RoboCopy(), logger, user_log=log_path).run():
			exit(1)
		exit(0)
	Gui(config, labels, settings, logger, user_log=log_path, source=source_path).mainloop()	# launch gui window 
