#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv, exit
from subprocess import Popen, PIPE, STARTUPINFO, STARTF_USESHOWWINDOW, run, CompletedProcess
from classes.path import Path

class Console:
	"""Interactive console prompts"""

	@staticmethod
	def ask_yes_no(prompt: str, default: bool = False) -> bool:
		"""Ask a yes/no question; empty input keeps default"""
		suffix = " [Y/n] " if default else " [y/N] "
		answer = input(prompt + suffix).strip().lower()
		if not answer:
			return default
		return answer in ("y", "yes")

	@staticmethod
	def info(message: str) -> None:
		print(message)

	@staticmethod
	def error(message: str) -> None:
		print(message)

class RoboCopyMirror:
	"""Mirror a directory with robocopy.exe /mir"""

	SUCCESS_MAX = 7  # Robocopy: 0–7 = success, >= 8 = failure

	def __init__(self, source: Path, destination: Path) -> None:
		self.source = Path(source).resolve()
		self.destination = Path(destination).resolve()
		if not self.source.is_dir():
			raise NotADirectoryError(f"Source is not a directory: {self.source}")
		self.destination.mkdir(parents=True, exist_ok=True)
		self.returncode: int | None = None

	@property
	def cmd(self) -> list[str]:
		return ["robocopy.exe", f"{self.source}", f"{self.destination}", "/mir"]

	def run(self, echo: bool = True) -> int:
		"""Run robocopy; stream stdout; raise RuntimeError on failure"""
		startupinfo = STARTUPINFO()
		startupinfo.dwFlags |= STARTF_USESHOWWINDOW
		if echo:
			Console.info(" ".join(self.cmd))
		proc = Popen(
			self.cmd,
			stdout=PIPE,
			stderr=PIPE,
			text=True,
			encoding="utf-8",
			errors="replace",
			startupinfo=startupinfo,
		)
		assert proc.stdout is not None
		for line in proc.stdout:
			if echo:
				print(line, end="")
		self.returncode = proc.wait()
		if self.returncode is not None and self.returncode > self.SUCCESS_MAX:
			err = proc.stderr.read() if proc.stderr else ""
			if err and echo:
				print(err, end="")
			raise RuntimeError(f"robocopy failed with exit code {self.returncode}")
		return self.returncode or 0

class DesktopShortcut:
	"""Windows .lnk shortcut on the user desktop"""

	def __init__(
		self,
		target: Path,
		name: str = "Cirdan",
		description: str = "Cirdan",
	) -> None:
		self.target = Path(target).resolve()
		self.name = name
		self.description = description
		if not self.target.is_file():
			raise FileNotFoundError(f"Shortcut target not found: {self.target}")

	@staticmethod
	def _ps_quote(value: str) -> str:
		"""Single-quote a string for PowerShell"""
		return "'" + value.replace("'", "''") + "'"

	@property
	def icon_location(self) -> str:
		icon = self.target.parent / "icons" / "cirdan.ico"
		return str(icon) if icon.is_file() else f"{self.target},0"

	def _powershell_script(self) -> str:
		q = self._ps_quote
		return f"""
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$lnkPath = Join-Path $desktop {q(self.name + '.lnk')}
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = {q(str(self.target))}
$shortcut.WorkingDirectory = {q(str(self.target.parent))}
$shortcut.IconLocation = {q(self.icon_location)}
$shortcut.Description = {q(self.description)}
$shortcut.Save()
Write-Output $lnkPath
"""

	def create(self) -> Path:
		"""Create the shortcut and return the .lnk path"""
		result: CompletedProcess[str] = run(
			["powershell.exe", "-NoProfile", "-Command", self._powershell_script()],
			capture_output=True,
			text=True,
			encoding="utf-8",
			errors="replace",
			check=False,
		)
		if result.returncode != 0:
			raise RuntimeError(
				result.stderr.strip() or f"powershell failed ({result.returncode})"
			)
		lines = (result.stdout or "").strip().splitlines()
		if not lines:
			raise RuntimeError("Desktop shortcut was not created")
		return Path(lines[-1])

class WinInstaller:
	"""Install by mirroring with robocopy, optionally create a desktop shortcut"""

	def __init__(self, source: Path | str, destination: Path | str) -> None:
		self.source = Path(source)
		self.destination = Path(destination)
		self.cirdan_exe = self.destination.resolve() / "cirdan.exe"

	def mirror(self) -> None:
		"""Mirror source into destination"""
		RoboCopyMirror(self.source, self.destination).run()

	def offer_desktop_shortcut(self) -> Path | None:
		"""Interactively offer a desktop shortcut to cirdan.exe"""
		if not self.cirdan_exe.is_file():
			Console.info(f"Note: {self.cirdan_exe} not found — skipping desktop shortcut")
			return None
		if not Console.ask_yes_no("Create a desktop shortcut to cirdan.exe?"):
			return None
		lnk = DesktopShortcut(self.cirdan_exe).create()
		Console.info(f"Desktop shortcut created: {lnk}")
		return lnk

	def run(self) -> None:
		"""Full install flow"""
		self.mirror()
		try:
			self.offer_desktop_shortcut()
		except Exception as ex:
			Console.error(f"Could not create desktop shortcut: {ex}")

if __name__ == "__main__":
	if len(argv) != 3:
		raise SystemExit(f"Usage: {argv[0]} <sourcedir> <destinationdir>")
	try:
		WinInstaller(argv[1], argv[2]).run()
	except Exception as ex:
		raise SystemExit(str(ex)) from ex
	exit(0)
