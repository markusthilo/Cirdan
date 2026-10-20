#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Markus Thilo"
__version__ = "2.0.0-Dev_2026-10-20"
__license__ = "GPL-3"
__email__ = "markus.thilo@proton.me"
__status__ = "Development"
__description__ = "Copy to Import/Remote Directory Across Network - a custom upload/copy tool"

from sys import exit
from traceback import format_exc
from argparse import ArgumentParser
from classes.path import Path
from classes.settings import Settings
from classes.logger import Logger
from classes.source import Source
from classes.worker import Worker
from classes.gui import Gui

if __name__ == "__main__":  # start here when run as application
	argparser = ArgumentParser(description=__description__)
	argparser.add_argument("-c", "--config", type=Path, metavar="FILE",
		help="Use the given config file instead of config.json in the application directory")
	argparser.add_argument("-d", "--destination", type=str, metavar="STRING",
		help="Destination to copy to")
	argparser.add_argument("-g", "--gui", action="store_true",
		help="Force GUI mode (default when no source directory is given)")
	argparser.add_argument("-l", "--log", type=Path, metavar="FILE",
		help="File to store log")
	argparser.add_argument("-m", "--mail", type=str, metavar="STRING",
		help="Send e-mail when copy process has finished, argument is mail address without domain (e.g. john.doe for john.doe@example.net)")
	argparser.add_argument("-n", "--nocheck", action="store_true",
		help="Disable checking source tree (blacklist, path length)")
	argparser.add_argument("-p", "--path", type=Path, metavar="DIRECTORY",
		help='Path of parent directory to copy to (overwrites "destinations"/"path" in config file, needs -d/--destination)')
	argparser.add_argument("-s", "--subject", type=str, metavar="STRING",
		help="Use the given subject for the e-mail")
	argparser.add_argument("-t", "--todo", type=str, metavar="STRING",
		help="Write metadata file, parameter will select the metadata content (needs -d/--destination)")
	argparser.add_argument("-u", "--username", type=str, metavar="STRING",
		help="Use the given username instead of logon")
	argparser.add_argument("-v", "--version", action="store_true",
		help="Print version number")
	argparser.add_argument("source", nargs="?", help="Source directory", type=Path, metavar="DIRECTORY")
	args = argparser.parse_args()
	if args.version:
		print(__version__)
		exit(0)
	use_gui = args.gui or not args.source
	if args.path and not args.destination:
		msg = "Destination (-d/--destination) is required when using -p/--path"
		if use_gui:
			Gui.startup_error(msg)
		raise RuntimeError(msg) from None
	if args.todo and not args.destination:
		msg = "Destination (-d/--destination) is required when using -t/--todo"
		if use_gui:
			Gui.startup_error(msg)
		raise RuntimeError(msg) from None
	try:	# handle startup error before logging
		settings = Settings(
			__version__,
			config = args.config,
			destination = args.destination,
			destination_path = args.path,
			todo = args.todo,
			no_source_check = args.nocheck,
			username = args.username,
			mail_to = args.mail,
			mail_subject = args.subject,
			user_log = args.log,
		)
		logger = Logger(settings)
	except Exception:	# error before logging
		msg = format_exc()
		if use_gui:
			Gui.startup_error(msg)
		raise RuntimeError(msg) from None
	try:	# now we have logging
		source_path = args.source.resolve() if args.source else None
		settings.set_todo(args.todo)
	except Exception:
		msg = logger.crash()
		if use_gui:
			Gui.startup_error(msg)
		raise RuntimeError(msg) from None
	if  use_gui:	# gui mode
		Gui(settings, logger, source_path).mainloop()	# launch gui window
	else:	# console mode
		if not source_path.is_dir():
			msg = logger.crash(f"Source is not a directory: {source_path}")
			raise RuntimeError(msg) from None
		if Worker([Source(source_path, settings)], settings, logger).run():
			exit(1)
	exit(0)
	