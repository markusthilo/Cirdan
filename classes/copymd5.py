#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import executable as __executable__
from platform import system
from subprocess import Popen, PIPE
from threading import Thread
from classes.path import Path

__system__ = system()
if Path(__executable__).name.startswith("python"):
	__app_path__ = Path(__file__).parent.parent
else:
	__app_path__ = Path(__executable__).parent

if __system__ == "Windows":
	from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW
	__binary_name__ = "copymd5.exe"
elif __system__ == "Linux":
	__binary_name__ = "copymd5"
else:
	raise RuntimeError(f"Unsupported platform: {__system__}")

class CopyMD5(Popen):
	"""Wrapper for the copymd5 binary"""

	def __init__(self, source: Path, destination: Path, tsv: Path) -> None:
		self.source = source
		self.destination = destination
		self.tsv = tsv
		self.binary = (__app_path__ / __binary_name__).resolve()
		if not self.binary.is_file():
			raise FileNotFoundError(f"copymd5 binary not found: {self.binary}")
		self.cmd = [str(self.binary), str(self.source), str(self.destination), str(self.tsv)]
		kwargs: dict[str, object] = {
			"stdout": PIPE,
			"stderr": PIPE,
			"text": True,
			"encoding": "utf-8",
			"errors": "replace",
			"bufsize": 1,
		}
		if __system__ == "Windows":
			startupinfo = STARTUPINFO()
			startupinfo.dwFlags |= STARTF_USESHOWWINDOW
			kwargs["startupinfo"] = startupinfo
		super().__init__(self.cmd, **kwargs)

	def __repr__(self) -> str:
		"""Return command line as string"""
		return f'{self.binary.name} "{self.source}" "{self.destination}" "{self.tsv}"'
