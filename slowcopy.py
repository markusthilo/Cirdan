#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.9.0_2025-04-27'
__license__ = 'GPL-3'
__email__ = 'markus.thilomarkus@gmail.com'
__status__ = 'Testing'
__description__ = 'Copy to import folder and generate trigger file'

from sys import executable as __executable__
from argparse import ArgumentParser
from pathlib import Path
from lib.config import Config
from lib.worker import Worker
from lib.gui import Gui

__parent_path__ = Path(__file__).parent if Path(__executable__).name == 'python.exe' else Path(__executable__).parent

if __name__ == '__main__':  # start here when run as application
	argparser = ArgumentParser(prog=f'SlowCopy Version {__version__}', description='Copy into MSD network')
	argparser.add_argument('-g', '--gui', action='store_true',
		help='Use GUI with given root directory as command line parameters.')
	argparser.add_argument('-l', '--log', type=Path,
		help='File to store log. No local log if not given.')
	argparser.add_argument('-n', '--notrigger', action='store_true',
		help='Do not triggedr further process to handle/move uploaded data.')
	argparser.add_argument('source', nargs='?', help='Source directory', type=Path, metavar='DIRECTORY')
	args = argparser.parse_args()
	config = Config(Path(__parent_path__, 'config.json'))
	if args.source and not args.gui:	# run in terminal
		work = Worker([args.source], config, log_dir=args.log, trigger=not args.notrigger)
	else:	# open gui if no argument is given
		Gui(args.source, config, __parent_path__, __version__, log_dir=args.log, trigger=not args.notrigger).mainloop()
