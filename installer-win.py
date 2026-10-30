#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os.path import normcase
from sys import argv, exit
from argparse import ArgumentParser
from subprocess import Popen, PIPE, STARTUPINFO, STARTF_USESHOWWINDOW, run, CompletedProcess
from classes.path import Path
from classes.settings import Config

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
	def ask_path(prompt: str, default: Path | str) -> Path:
		"""Ask for a path; empty input keeps default"""
		default_path = Path(default)
		answer = input(f"{prompt} [{default_path}]: ").strip().strip('"')
		return Path(answer) if answer else default_path

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
		self.returncode: int | None = None

	@property
	def cmd(self) -> list[str]:
		# /xd /xf skip __pycache__ and any name starting with a dot (.git, .gitignore, ...)
		return [
			"robocopy.exe", f"{self.source}", f"{self.destination}",
			"/mir",
			"/xd", ".*", "__pycache__",
			"/xf", ".*",
		]

	def ensure_destination(self, echo: bool = True) -> None:
		"""Create the destination directory (and parents) if missing"""
		if not self.destination.is_dir():
			if echo:
				Console.info(f"Creating {self.destination}")
			self.destination.mkdir(parents=True, exist_ok=True)

	def run(self, echo: bool = True) -> int:
		"""Run robocopy; stream stdout; raise RuntimeError on failure"""
		self.ensure_destination(echo=echo)
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
	def lnk_path(name: str = "Cirdan") -> Path:
		"""Filesystem path of the shortcut on the user desktop"""
		desktop = Path.home() / "Desktop"
		try:
			from ctypes import create_unicode_buffer, windll
			buf = create_unicode_buffer(32767)
			# CSIDL_DESKTOPDIRECTORY: the real folder, including a redirected desktop
			if windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0 and buf.value:
				desktop = Path(buf.value)
		except (AttributeError, ImportError, OSError):
			pass
		return desktop / f"{name}.lnk"

	@staticmethod
	def read_target(lnk: Path) -> Path | None:
		"""Target path stored in an existing .lnk, if it can be read"""
		if not lnk.is_file():
			return None
		script = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut({DesktopShortcut._ps_quote(str(lnk))})
Write-Output $shortcut.TargetPath
"""
		result = run(
			["powershell.exe", "-NoProfile", "-Command", script],
			capture_output=True,
			text=True,
			encoding="utf-8",
			errors="replace",
			check=False,
		)
		if result.returncode != 0:
			return None
		target = (result.stdout or "").strip()
		return Path(target) if target else None

	@staticmethod
	def points_to(target: Path, install_dir: Path) -> bool:
		"""True when the shortcut target is cirdan.exe inside install_dir"""
		try:
			target_dir = target.resolve().parent
			install = install_dir.resolve()
		except OSError:
			target_dir = target.parent
			install = install_dir
		return normcase(str(target_dir)) == normcase(str(install)) and target.name.lower() == "cirdan.exe"

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

	DEFAULT_INSTALL_DIR = Path("C:/Programm Files/Cirdan")

	def __init__(self, source: Path | str, destination: Path | str) -> None:
		self.source = Path(source)
		self.destination = Path(destination)
		self.cirdan_exe = self.destination.resolve() / "cirdan.exe"

	@classmethod
	def from_argv(cls, args: list[str]) -> "WinInstaller":
		"""Source comes from Config; one optional argument is the install directory"""
		parser = ArgumentParser(
			description="Install Cirdan by mirroring the source directory from config.json (update_path)",
		)
		parser.add_argument(
			"destination",
			nargs="?",
			type=Path,
			metavar="DIRECTORY",
			help=f"Install directory. If omitted, you will be asked (default: {cls.DEFAULT_INSTALL_DIR})",
		)
		parsed = parser.parse_args(args)
		source = Config().update_path
		Console.info(f"Source: {source}")
		destination = parsed.destination or Console.ask_path("Install directory", cls.DEFAULT_INSTALL_DIR)
		return cls(source, destination)

	def ensure_destination(self) -> None:
		"""Create the install directory if it does not exist"""
		dest = self.destination.resolve()
		if not dest.is_dir():
			Console.info(f"Creating {dest}")
			dest.mkdir(parents=True, exist_ok=True)

	def mirror(self) -> None:
		"""Mirror source into destination (creates destination if needed)"""
		RoboCopyMirror(self.source, self.destination).run()

	def offer_desktop_shortcut(self) -> Path | None:
		"""Ask for a desktop shortcut unless it already points at this install directory"""
		lnk = DesktopShortcut.lnk_path()
		install_dir = self.destination.resolve()
		current = DesktopShortcut.read_target(lnk) if lnk.is_file() else None
		if current is not None and DesktopShortcut.points_to(current, install_dir):
			Console.info(f"Desktop shortcut already points to {install_dir}")
			return lnk
		if not self.cirdan_exe.is_file():
			Console.info(f"Note: {self.cirdan_exe} not found — skipping desktop shortcut")
			return None
		if lnk.is_file():
			Console.info(f"Desktop shortcut points to {current or 'unknown'}")
		if not Console.ask_yes_no("Create a desktop shortcut to cirdan.exe?", default=True):
			return None
		lnk = DesktopShortcut(self.cirdan_exe).create()
		Console.info(f"Desktop shortcut created: {lnk}")
		return lnk

	def run(self) -> None:
		"""Full install flow"""
		self.ensure_destination()
		self.mirror()
		try:
			self.offer_desktop_shortcut()
		except Exception as ex:
			Console.error(f"Could not create desktop shortcut: {ex}")

if __name__ == "__main__":
	try:
		WinInstaller.from_argv(argv[1:]).run()
	except Exception as ex:
		raise SystemExit(str(ex)) from ex
	exit(0)
