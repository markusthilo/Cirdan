#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tempfile import TemporaryDirectory
from classes.path import Path
from classes.copymd5 import CopyMD5

if __name__ == "__main__":
	with TemporaryDirectory() as tmp:
		tmp_path = Path(tmp)
		src = tmp_path / "src"
		dst = tmp_path / "dst"
		src.mkdir()
		dst.mkdir()
		(src / "hello.txt").write_text("hello copymd5\n", encoding="utf-8")
		print(f"Running CopyMD5({src}, {dst})")
		copy = CopyMD5(src, dst)
		print(copy)
		assert copy.stdout is not None
		for line in copy.stdout:
			print(line, end="")
		if err := copy.read_stderr():
			print(err, end="")
		rc = copy.wait()
		copied = dst / src.name / "hello.txt"
		print(f"returncode={rc}")
		if copied.is_file():
			print(f"copied exists=True content={copied.read_text(encoding='utf-8')!r}")
		else:
			print(f"copied missing: {copied}")
		raise SystemExit(rc)
