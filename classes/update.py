#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from sys import executable as executable
from shutil import which
from classes.path import Path
from platform import system
from subprocess import Popen

__executable__ = Path(executable)
__system__ = system()
if __system__ == "Windows":
	from subprocess import CREATE_NEW_CONSOLE

class Update:
	"""Check for new version and start download if available"""

	INSTALLER_EXE = "installer-win.exe"

	@staticmethod
	def _int(version: str) -> int:
		"""Convert version string into an integer"""
		try:
			version, date = version.split("_", 1)
			date_equivalent = int(datetime.fromisoformat(date).timestamp()) // 86400
		except ValueError:
			date_equivalent = 0
		equivalent = 0
		for i, digit in enumerate[tuple[int, str]](version.split(".")[:3]):
			try:
				equivalent += int(digit) * 10**(10-(i*2))
			except ValueError:
				pass
		equivalent += date_equivalent
		return equivalent

	def __init__(self, this_version: str, src_path: Path | str, install_path: Path | str) -> None:
		"""Check for newer version"""
		self.new_version: str | None = None
		self._src_path = Path(src_path).resolve()
		self._install_path = Path(install_path).resolve()
		self.installer_cmd: list[str] | None = None
		if self._install_path.as_posix().startswith("//"):
			return
		try:
			remote_version = self._src_path.joinpath("version.txt").read_text(encoding="utf-8").strip()
		except OSError:
			return
		self.new_version = remote_version if self._int(remote_version) > self._int(this_version) else None
		if self.new_version is None:
			return
		installer_path = self._src_path.joinpath(Update.INSTALLER_EXE)
		if __system__ == "Windows" and not __executable__.name.startswith("python") and installer_path.is_file():
			self.installer_cmd = [f"{installer_path}", f"{self._install_path}"]

	def install(self) -> Popen[bytes]:
		"""Launch installer"""
		if self.installer_cmd :
			return Popen(self.installer_cmd)
