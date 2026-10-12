#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Markus Thilo"
__version__ = "2.0.0-Dev_2026-10-12"
__license__ = "GPL-3"
__email__ = "markus.thilo@proton.me"
__status__ = "Development"
__description__ = "Copy to Import/Remote Directory Across Network - a custom upload/copy tool"

from sys import exit
from traceback import format_exc
from argparse import ArgumentParser
from classes.path import Path
from classes.labels import Labels
from classes.config import Config
from classes.settings import Settings
from classes.logger import Logger
from classes.source import Source
from classes.todo import ToDo
from classes.worker import Worker
from classes.gui import Gui

if __name__ == "__main__":  # start here when run as application
	argparser = ArgumentParser(description=__description__)
	argparser.add_argument('-c', '--config', type=Path, metavar='FILE',
		help="Use the given config file instead of the default in the application directory")
	argparser.add_argument("-d", "--destination", type=str, metavar="STRING",
		help="Destination to copy to")
	argparser.add_argument("-g", "--gui", action="store_true",
		help="Use GUI with given root directory as command line parameters")
	argparser.add_argument("-l", "--log", type=Path, metavar="FILE",
		help="File to store log")
	argparser.add_argument("-m", "--mail", type=str, metavar="STRING",
		help="Send e-mail when copy process has finished, argument is mail address without domain (e.g. john.doe for john.doe@example.net)")
	argparser.add_argument("-n", "--nocheck", action="store_true",
		help="Disable path checks (whitelist, blacklist, length)")
	argparser.add_argument("-r", "--remote", type=Path, metavar="DIRECTORY",
		help='Path of parent directory to copy to (overwrites "remote_path" in config file, needs -d/--destination to be set)')
	argparser.add_argument("-s", "--subject", type=str, metavar="STRING",
		help="Use the given subject for the e-mail (in Casewhen copy process has finished, argument is mail address without domain (e.g. john.doe for john.doe@example.net)")
	argparser.add_argument("-t", "--todo", type=str, metavar="STRING",
		help="Write metadata file, parameter will select the metadata content")
	argparser.add_argument("-u", "--username", type=str, metavar="STRING",
		help="Use the given username instead of logon")
	argparser.add_argument("-v", "--version", action="store_true",
		help="Print version number")
	argparser.add_argument("source", nargs="?", help="Source directory", type=Path, metavar="DIRECTORY")
	args = argparser.parse_args()
	if args.version:
		print(__version__)
		exit(0)
	if args.path and not args.destination:
		msg = "Destination (-r/--remote) is required when using -p/--path"
		Gui.startup_error(msg)
		argparser.error(msg)
	try:	# handle startup error before logging
		config = Config(args.config)
		settings = Settings(config, args.destination, args.username, args.mail, args.subject)
		labels = Labels(config, __version__)
		logger = Logger(config, settings, labels)
	except:	# error before logging
		msg = format_exc()
		if not args.source or args.gui:
			Gui.startup_error(msg)	# show error message in window
		raise RuntimeError(msg)
	try:	# now we have logging
		source_path = args.source.resolve() if args.source else None
		config.gen_destination_paths()
	except Exception:
		msg = logger.crash()
		if not args.source or args.gui:
			Gui.startup_error(msg)	# show error message in window
		raise RuntimeError(msg)
	todo = ToDo(args.todo, settings, config)
	if source_path and not args.gui:	# no gui
		settings.sendmail = bool(args.mail)
		settings.mail_to = args.mail
		settings.mail_subject = args.subject
		if not config.log_path.is_accessable_dir():
			logger.crash(labels.bad_log_dir.replace("#", f"{config.log_path}"))
			exit(1)
		if not args.mail:
			settings.sendmail = False
		if Worker(
			[
				Source(source_path,
					max_path_len = None if args.nocheck else config.max_path_length,
					whitelist = None if args.nocheck else config.source_whitelist,
					blacklist = None if args.nocheck else config.source_blacklist,
					countlist = config.count_paths
				)
			],
			todo,
			config,
			labels,
			settings,
			logger,
			user_log = args.log,
		).run():
			exit(1)
		exit(0)
	if args.mail:
		settings.mail_to = args.mail
		if args.subject:
			settings.mail_subject = args.subject
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
