#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from platform import system
from sys import argv, executable
from subprocess import Popen
from classes.path import Path

__executable__ = Path(executable)


if __name__ == "__main__":
	if len(argv) != 3:
		raise SystemExit(f"Usage: {argv[0]} <source-dir> <destination-dir>")
	src_path = Path(argv[1])
	dst_path = Path(argv[2])
	src_path.mirror_dir_into(dst_path, echo=print)

	exe_name = __executable__.name
	Popen([str(__executable__)], start_new_session=True)