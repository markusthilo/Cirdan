#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections.abc import Generator
from pathlib import Path as PathlibPath
from time import strftime
from classes.size import Size

class Path(PathlibPath):
	"""Methods to check and create paths"""

	if not hasattr(PathlibPath, "copy"):	# pathlib.Path.copy exists from Python 3.14
		def copy(self, destination: Path) -> Path:
			"""Copy file to destination (Python < 3.14)"""
			destination.write_bytes(self.read_bytes())
			return destination

	def __repr__(self) -> str:
		"""Readable representation with forward slashes (do not use as_posix: it calls str())"""
		return PathlibPath.__str__(self).replace("\\", "/")

	def timed(self, fmt: str = "%y%m%d_%H%M%S_%n") -> Path:
		"""Return path with timestamp added to name (%n = original name)"""
		return self.with_name(strftime(fmt.replace("%n", self.name)))

	def append_name(self, name: str, use_strftime: bool = False) -> Path:
		"""Append name to path; optionally expand strftime codes in name"""
		return self.joinpath(strftime(name) if use_strftime else name)

	def get_filesize(self) -> Size:
		"""Return size of file"""
		return Size(self.stat().st_size)

	def is_accessible(self) -> bool:
		"""Check if path is an accessible directory (iterdir can fail in AD environments)"""
		try:
			if not self.is_dir():
				return False
			next(iter(self.iterdir()), None)
			return True
		except OSError:
			return False

	def rrglob(
		self,
		pattern: str,
		case_sensitive: bool | None = None,
		recurse_symlinks: bool = False,
	) -> Generator[tuple[Path, str], None, None]:
		"""Recursive glob yielding (path, relative posix path including parent name)"""
		resolved = self.resolve()
		for path in resolved.rglob(
			pattern,
			case_sensitive=case_sensitive,
			recurse_symlinks=recurse_symlinks,
		):
			yield path, path.relative_to(resolved.parent).as_posix()

	def open_w(self):
		"""Open file to write utf-8 text"""
		return self.open(mode="w", encoding="utf-8")

	def mk(self) -> bool:
		"""Create directory if it does not already exist as an accessible dir"""
		if self.is_accessible():
			return False
		self.mkdir(parents=True, exist_ok=True)
		return True

	def write_text_file(self, filename: str, text: str, use_strftime: bool = False) -> int:
		"""Write text to a file under this directory"""
		return self.append_name(filename, use_strftime=use_strftime).write_text(text, encoding="utf-8")
