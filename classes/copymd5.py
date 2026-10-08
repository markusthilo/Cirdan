#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import executable as __executable__
from platform import system
from classes.path import Path

__system__ = system()
if __system__ == "Windows":
    from subprocess import Popen, STARTUPINFO, STARTF_USESHOWWINDOW, PIPE, STDOUT
    __app_path__ = Path(__file__).parent.parent if Path(__executable__).name.startswith('python') else Path(__executable__).parent
elif __system__ == "Linux":
    from subprocess import Popen, PIPE, STDOUT
    __app_path__ = Path(__file__).parent.parent
else:
    raise RuntimeError(f"Unsupported platform: {__system__}")

class CopyMD5(Popen):
	"""Wrapper for copymd5"""

	def __init__(self, source: Path, destination: Path) -> None:
		self.source = Path(source).absolute()
		self.destination = Path(destination).absolute()
		if __system__ == "Windows":
			startupinfo = STARTUPINFO()
			startupinfo.dwFlags |= STARTF_USESHOWWINDOW
			self.cmd = [__app_path__ / "copymd5.exe", self.source, self.destination]
			super().__init__(
				self.cmd,
				startupinfo=startupinfo,
				stdout = PIPE,
				stderr = STDOUT,
				encoding = "utf-8",
				errors = "ignore",
				universal_newlines = True,
			)
		else:
			self.cmd = [__app_path__ / "copymd5", self.source, self.destination]
			super().__init__(
				self.cmd,
				stdout = PIPE,
				stderr = STDOUT,
				encoding = "utf-8",
				errors = "ignore",
				universal_newlines = True,
			)

	def __repr__(self):
		"""Return command line as string"""
		return f'{self.cmd[0]} "{self.source}" "{self.destination}"'
