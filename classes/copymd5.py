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

	def __init__(self, source: Path, destination: Path) -> None:
		self.source = Path(source).resolve()
		self.destination = Path(destination).resolve()
		binary = (__app_path__ / __binary_name__).resolve()
		if not binary.is_file():
			raise FileNotFoundError(f"copymd5 binary not found: {binary}")
		self.cmd = [str(binary), str(self.source), str(self.destination)]
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
		self._stderr_chunks: list[str] = []
		self._stderr_thread = Thread(target=self._drain_stderr, daemon=True)
		self._stderr_thread.start()

	def _drain_stderr(self) -> None:
		"""Read stderr in the background so a full pipe cannot deadlock stdout"""
		if self.stderr is not None:
			self._stderr_chunks.append(self.stderr.read())

	def read_stderr(self) -> str:
		"""Return stderr collected while stdout was consumed"""
		self._stderr_thread.join(timeout=5)
		return "".join(self._stderr_chunks)

	def __repr__(self) -> str:
		"""Return command line as string"""
		return f'{self.cmd[0]} "{self.source}" "{self.destination}"'
