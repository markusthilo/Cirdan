#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from platform import system
from sys import argv, executable
from subprocess import Popen
from classes.path import Path

def _remove_tree(path: Path) -> None:
	"""Remove a file or directory tree using pathlib only"""
	if path.is_dir() and not path.is_symlink():
		for child in path.iterdir():
			_remove_tree(child)
		path.rmdir()
	else:
		path.unlink(missing_ok=True)

def mirror_dir(src: Path, dst: Path) -> None:
	"""
	Mirror src into dst (copy/update all entries, then delete extras in dst).
	Prints each relative path as it is copied or removed.
	"""
	src = src.resolve()
	dst = dst.resolve()
	if not src.is_dir():
		raise NotADirectoryError(f"Source is not a directory: {src}")
	dst.mkdir(parents=True, exist_ok=True)

	for path in src.rglob("*"):
		relative = path.relative_to(src)
		target = dst / relative
		if path.is_dir():
			target.mkdir(parents=True, exist_ok=True)
			print(f"{relative.as_posix()}/")
		elif path.is_file():
			target.parent.mkdir(parents=True, exist_ok=True)
			path.copy(target)
			print(relative.as_posix())

	# Delete destination entries that no longer exist in source (depth-first)
	for path in sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True):
		relative = path.relative_to(dst)
		if not (src / relative).exists():
			print(f"deleted {relative.as_posix()}")
			_remove_tree(path)

def _launch_app(dst_path: Path) -> None:
	"""Start the installed Cirdan from the destination directory"""
	exe_name = Path(executable).name
	if system() == "Windows" and (dst_path / "cirdan.exe").is_file() and not exe_name.startswith("python"):
		cmd = [str(dst_path / "cirdan.exe")]
	else:
		cmd = ["python", str(dst_path / "cirdan.py")]
	Popen(cmd, start_new_session=True)

if __name__ == "__main__":
	if len(argv) < 3:
		raise SystemExit(f"Usage: {argv[0]} <source> <destination>")
	src_path = Path(argv[1])
	dst_path = Path(argv[2])
	try:
		mirror_dir(src_path, dst_path)
		_launch_app(dst_path)
	except Exception as ex:
		print(f"{type(ex).__name__}: {ex}")
		input("Press Enter to close installer...")
		raise SystemExit(1) from ex
