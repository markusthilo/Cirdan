#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from sys import executable as executable
from shutil import which
from classes.path import Path
from platform import system
from subprocess import CREATE_NEW_CONSOLE, Popen

__executable__ = Path(executable)

class Update:
	"""Check for new version and start download if available"""

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

	def __init__(self, this_version: str, src_path: Path | str) -> None:
		"""Check for newer version"""
		self.new_version: str | None = None
		self._path = Path(src_path).resolve()
		try:
			remote_version = self._path.joinpath("version.txt").read_text(encoding="utf-8").strip()
		except OSError:
			return
		self.new_version = remote_version if self._int(remote_version) > self._int(this_version) else None

	def download(self, install_path: Path | str) -> Popen[bytes]:
		"""Launch update downloader in a new terminal"""
		install_path = Path(install_path).resolve()
		if __executable__.name.startswith("python"):
			cmd: list[str | Path] = ["python", self._path / "downloader.py"]
		elif system() == "Windows":
			cmd = [self._path / "downloader.exe"]
		cmd.append(self._path)
		cmd.append(install_path)
		return self._open_terminal([str(part) for part in cmd])

	@staticmethod
	def _open_terminal(cmd: list[str]) -> Popen[bytes]:
		"""Open cmd in a new console on Windows or a terminal emulator on Linux"""
		if system() == "Windows":
			return Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
		terminals = (
			("konsole", ("konsole", "-e")),
			("gnome-terminal", ("gnome-terminal", "--")),
			("xfce4-terminal", ("xfce4-terminal", "-x")),
			("mate-terminal", ("mate-terminal", "-x")),
			("kitty", ("kitty",)),
			("alacritty", ("alacritty", "-e")),
			("xterm", ("xterm", "-e")),
			("x-terminal-emulator", ("x-terminal-emulator", "-e")),
		)
		for name, prefix in terminals:
			if which(name):
				return Popen([*prefix, *cmd], start_new_session=True)
		raise FileNotFoundError("No terminal emulator found")
