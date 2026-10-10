#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tempfile import TemporaryDirectory
from classes.path import Path
from classes.copymd5 import CopyMD5

if __name__ == "__main__":
	with TemporaryDirectory() as tmp:
		tmp = Path(tmp)
		src = tmp / "src"
		dst = tmp / "dst"
		src.mkdir()
		dst.mkdir()
		(src / "hello.txt").write_text("hello copymd5\n", encoding="utf-8")
		print(f"Running CopyMD5({src}, {dst})")
		copy = CopyMD5(src, dst)
		print(copy)
		for line in copy.stdout:
			print(line, end="")
		if copy.stderr:
			err = copy.stderr.read()
			if err:
				print(err, end="")
		rc = copy.wait()
		copied = dst / src.name / "hello.txt"
		print(f"returncode={rc}")
		print(f"copied exists={copied.is_file()} content={copied.read_text(encoding='utf-8')!r}" if copied.is_file() else f"copied missing: {copied}")
		raise SystemExit(rc)
