#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '1.6.1_2026-09-17'
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
from classes.source import Source
from classes.todo import ToDo
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
	argparser.add_argument('-l', '--log', type=Path, metavar='FILE',
		help='File to store log')
	argparser.add_argument('-m', '--mail', type=str, metavar='STRING',
		help='Send e-mail when copy process has finished, argument is mail address without domain (e.g. john.doe for john.doe@example.net)')
	argparser.add_argument('-n', '--nocheck', action='store_true',
		help='Disable path checks (whitelist, blacklist, length)')
	argparser.add_argument('-q', '--qualicheck', action='store_true',
		help='Initiate qualicheck when the entire process has finished')
	argparser.add_argument('-s', '--subject', type=str, metavar='STRING',
		help='Use the given subject for the e-mail (in Casewhen copy process has finished, argument is mail address without domain (e.g. john.doe for john.doe@example.net)')
	argparser.add_argument('-t', '--todo', type=str, metavar='STRING',
		help='Write metadata file, parameter will select the metadata content')
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
		source_path = args.source.resolve() if args.source else None
		config.reachable_dsts = {
			key: value for key, value in config.destinations.items()
			if config.target_path.joinpath(value['sub_path']).is_accessable_dir()
		}
		if not config.reachable_dsts:
			raise NotADirectoryError(f'Unable to find or reach subdirectories of {config.target_path}')
		if settings.destination and not settings.destination in config.reachable_dsts:
			settings.destination = ''
		if not config.log_path.is_accessable_dir():
			raise NotADirectoryError(f'Unable to find or reach log directory {config.log_path}')
	except Exception as ex:
		msg = logger.crash(ex)
		if not args.source or args.gui:
			Gui.startup_error(msg)	# show error message in window
		exit(1)
	todo = ToDo(args.todo, settings, config)
	if source_path and not args.gui:	# no gui
		settings.sendmail = bool(args.mail)
		settings.user = args.mail
		settings.mail_subject = args.subject
		settings.qualicheck = args.qualicheck
		if not config.log_path.is_accessable_dir():
			logger.crash(labels.bad_log_dir.replace('#', f'{config.log_path}'))
			exit(1)
		if not args.mail:
			settings.sendmail = False
		if Worker(
			[
				Source(source_path,
					max_path_len = None if args.nocheck else config.max_path_length,
					whitelist = None if args.nocheck else config.source_whitelist,
					blacklist = None if args.nocheck else config.source_blacklist
				)
			],
			todo,
			config,
			labels,
			settings,
			RoboCopy(),
			logger,
			user_log = args.log
		).run():
			exit(1)
		exit(0)
	if args.mail:
		settings.user = args.mail
		if args.subject:
			settings.mail_subject = args.subject
	if args.qualicheck:
		settings.qualicheck = True
	Gui(
		config,
		labels,
		settings,
		logger,
		user_log = args.log,
		source = source_path,
		todo = todo,
		no_source_check = args.nocheck
	).mainloop()	# launch gui window 
