#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Markus Thilo"
__version__ = "2.1.0_2026-11-18"
__license__ = "GPL-3"
__email__ = "markus.thilo@proton.me"
__status__ = "Testing"
__description__ = "Copy to Import/Remote Directory Across Network - a custom upload/copy tool"

from sys import exit
from traceback import format_exc
from argparse import ArgumentParser
from classes.path import Path
from classes.settings import Settings
from classes.logger import Logger
from classes.source import Source
from classes.destination import Destination
from classes.worker import Worker
from classes.gui import Gui

if __name__ == "__main__":  # start here when run as application
	### private functions for error handling ###
	def _check_for_error(rel_path, error):
		"""Handle insertion error"""
		if isinstance(error, int):
			raise OSError(
				settings.labels.path_too_long.replace(
					"#1", str(rel_path)).replace(
					"#2", str(error)).replace(
					"#3", str(settings.max_path_length)
				)
			) from None
		elif isinstance(error, str):
			raise OSError(
				settings.labels.blacklisted.replace(
					"#1", str(rel_path)).replace(
					"#2", error
				)
			) from None
	### end of private functions for error handling ###
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
		help="Disable checking source tree (whitelist, blacklist, path length)")
	argparser.add_argument("-o", "--top", type=str, metavar="STRING",
		help="Top level directory name")
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
	argparser.add_argument("sources", nargs="*", help="Source directories or files", type=Path, metavar="DIRECTORY|FILE")
	args = argparser.parse_args()
	if args.version:
		print(__version__)
		exit(0)
	use_gui = args.gui or not args.sources
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
			destination_name = args.destination,
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
		source = Source(settings)
		if settings.no_source_check:
			source.set_no_check()
		if not use_gui:
			for arg in args.sources:
				if arg.is_dir():
					if top_dir := source.top_dir(arg):
						if source.top_dir_path:
							raise ValueError(settings.labels.top_dir_already_set)
						for rel_path, error in source.insert_top_dir(arg):
							_check_for_error(rel_path,error)
							print(f"{settings.labels.inserted} {rel_path}")
						continue
					if sub_dir := source.sub_dir(arg):
						if arg.name in source.sub_dirs.keys():
							raise ValueError(settings.labels.sub_dir_already_set.replace("#", arg.name))
						for rel_path, error in source.add_sub_dir(arg):
							_check_for_error(rel_path,error)
							print(f"{settings.labels.inserted} {rel_path}")
						continue
					if arg.is_file():
						if source.add_sub_file(arg):
							print(f"{settings.labels.inserted} {arg}")
		if args.top:
			source.set_top_dir_name(args.top)
		destination = Destination(settings) if settings.destination_name else None
	except Exception:
		msg = logger.crash()
		if use_gui:
			Gui.startup_error(msg)
		raise RuntimeError(msg) from None
	if  use_gui:	# gui mode
		Gui(settings, logger, source, destination, args.sources).mainloop()	# launch gui window
	else:	# console mode
		logger.add_remote(source)
		if settings.user_log:
			logger.add_user(settings.user_log)
		returncode = Worker(source, destination, settings).run()
		logger.close_user()
		logger.close_remote()
		exit(returncode)
