#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from sys import executable
from subprocess import Popen
from classes.path import Path

class Update:
	"""Check for new version and start download if available"""

	@staticmethod
	def _int(string: str) -> int:
		"""Convert version string into an integer"""
		try:
			version, date = string.split("_", 1)
			parts = [int(part) for part in version.split(".", 2)]
			while len(parts) < 3:
				parts.append(0)
			return (
				sum(value * weight for value, weight in zip(parts, (10_000_000_000, 100_000_000, 1_000_000)))
				+ int(datetime.fromisoformat(date).timestamp() / 86400)
			)
		except (ValueError, TypeError, OSError):
			return 0

	def __init__(self, this_version: str, src_path: Path | str) -> None:
		"""Check for newer version"""
		self._src_path = Path(src_path)
		try:
			new_version = self._src_path.joinpath("version.txt").read_text(encoding="utf-8").strip()
		except OSError:
			self.new_version: str | None = None
			return
		self.new_version = new_version if self._int(new_version) > self._int(this_version) else None

	def download(self, install_path: Path | str) -> Popen:
		"""Launch update downloader"""
		install_path = Path(install_path)
		if Path(executable).name.startswith("python"):
			cmd: list[str | Path] = ["python", self._src_path / "downloader.py"]
		else:
			cmd = [self._src_path / "downloader.exe"]
		cmd.append(self._src_path)
		cmd.append(install_path)
		return Popen([str(part) for part in cmd], start_new_session=True)
