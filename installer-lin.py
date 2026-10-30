#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv, exit
from os import R_OK, W_OK, X_OK, access
from argparse import ArgumentParser
from subprocess import run, CompletedProcess, DEVNULL
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

class Sudo:
	"""Run commands with sudo"""

	@staticmethod
	def run(cmd: list[str], echo: bool = True) -> CompletedProcess[str]:
		"""Execute cmd under sudo; raise RuntimeError on failure"""
		full = ["sudo", *cmd]
		if echo:
			Console.info(" ".join(full))
		result = run(full, text=True, encoding="utf-8", errors="replace", check=False)
		if result.returncode != 0:
			raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(full)}")
		return result

	@staticmethod
	def write_text(path: Path, text: str, echo: bool = True) -> None:
		"""Write text to path using sudo tee (stdout discarded so contents are not echoed)"""
		if echo:
			Console.info(f"sudo tee {path}")
		result = run(
			["sudo", "tee", str(path)],
			input=text,
			text=True,
			encoding="utf-8",
			errors="replace",
			stdout=DEVNULL,
			check=False,
		)
		if result.returncode != 0:
			raise RuntimeError(f"sudo tee failed for {path}")

class InstallCopy:
	"""Copy a source tree into an install directory with rsync -a, using sudo when needed"""

	def __init__(self, source: Path, destination: Path) -> None:
		self.source = Path(source).resolve()
		self.destination = Path(destination)
		self.used_sudo = False
		if not self.source.is_dir():
			raise NotADirectoryError(f"Source is not a directory: {self.source}")

	@staticmethod
	def user_can_rw(path: Path) -> bool:
		"""True when the user can replace path, including read-only files in a writable directory"""
		current = Path(path)
		if not current.exists():
			while not current.exists():
				parent = current.parent
				if parent == current:
					return False
				current = parent
			return current.is_dir() and access(current, R_OK | W_OK | X_OK)
		if not current.is_dir() or not access(current, R_OK | W_OK | X_OK):
			return False
		try:
			for child in current.rglob("*"):
				if child.is_dir() and not child.is_symlink() and not access(child, W_OK | X_OK):
					return False
		except OSError:
			return False
		return True

	def _run(self, cmd: list[str], use_sudo: bool) -> None:
		if use_sudo:
			self.used_sudo = True
			Sudo.run(cmd)
			return
		Console.info(" ".join(cmd))
		result = run(cmd, text=True, encoding="utf-8", errors="replace", check=False)
		if result.returncode != 0:
			raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")

	def ensure_destination(self, echo: bool = True) -> None:
		"""Create the destination directory (and parents) if missing"""
		if self.destination.is_dir():
			return
		if self.destination.exists():
			raise NotADirectoryError(f"Destination is not a directory: {self.destination}")
		if self.user_can_rw(self.destination):
			if echo:
				Console.info(f"Creating {self.destination}")
			self.destination.mkdir(parents=True, exist_ok=True)
			return
		self.used_sudo = True
		Sudo.run(["mkdir", "-p", str(self.destination)], echo=echo)

	def run(self) -> None:
		"""Create destination and copy source contents into it"""
		self.ensure_destination()
		# Trailing slash copies contents into destination (not a nested sourcedir/).
		# Exclude __pycache__ and any name starting with a dot (.git, .gitignore, ...).
		cmd = [
			"rsync", "-a",
			"--exclude", ".*",
			"--exclude", "__pycache__",
			f"{self.source}/",
			f"{self.destination}/",
		]
		self._run(cmd, use_sudo=not self.user_can_rw(self.destination))

class DesktopEntry:
	"""Freedesktop application launcher (.desktop)"""

	def __init__(
		self,
		install_dir: Path,
		desktop_path: Path,
		name: str = "Cirdan",
		script_name: str = "cirdan.py",
	) -> None:
		self.install_dir = Path(install_dir)
		self.desktop_path = Path(desktop_path)
		self.name = name
		self.script = self.install_dir / script_name
		self.icon = self.install_dir / "icons" / "cirdan.png"

	@property
	def content(self) -> str:
		return (
			"[Desktop Entry]\n"
			"Type=Application\n"
			"Version=1.0\n"
			f"Name={self.name}\n"
			"Comment=Copy to Import/Remote Directory Across Network\n"
			f"Exec=python3 {self.script}\n"
			f"Path={self.install_dir}\n"
			f"Icon={self.icon}\n"
			"Terminal=false\n"
			"Categories=Utility;FileTools;\n"
			"StartupNotify=true\n"
		)

	def create(self) -> Path:
		"""Write the .desktop file (requires sudo for system paths)"""
		Sudo.write_text(self.desktop_path, self.content)
		Sudo.run(["chmod", "644", str(self.desktop_path)])
		return self.desktop_path

class LinInstaller:
	"""Install Cirdan with cp -a and register a .desktop launcher"""

	DEFAULT_INSTALL_DIR = Path("/opt/Cirdan")
	DESKTOP_PATH = Path("/usr/share/applications/cirdan.desktop")

	def __init__(self, source: Path | str, destination: Path | str | None = None) -> None:
		self.source = Path(source)
		self.install_dir = Path(destination) if destination else self.DEFAULT_INSTALL_DIR
		self.desktop_path = self.DESKTOP_PATH
		self.used_sudo = False

	@classmethod
	def from_argv(cls, args: list[str]) -> "LinInstaller":
		"""Source comes from Config; one optional argument is the install directory"""
		parser = ArgumentParser(
			description="Install Cirdan by copying the source directory from config.json (update_path)",
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
		InstallCopy(self.source, self.install_dir).ensure_destination()

	def copy(self) -> None:
		"""Copy source tree into the install directory (creates destination if needed)"""
		install_copy = InstallCopy(self.source, self.install_dir)
		install_copy.run()
		self.used_sudo = install_copy.used_sudo

	def install_desktop_entry(self) -> Path:
		"""Create /usr/share/applications/cirdan.desktop"""
		path = DesktopEntry(self.install_dir, self.desktop_path).create()
		Console.info(f"Desktop entry created: {path}")
		return path

	def offer_desktop_entry(self) -> Path | None:
		"""Offer the applications-menu launcher when the install used sudo"""
		if not self.used_sudo:
			return None
		if not Console.ask_yes_no(
			f"Create application menu entry ({self.desktop_path})?",
			default=True,
		):
			return None
		return self.install_desktop_entry()

	def run(self) -> None:
		"""Full install flow"""
		self.ensure_destination()
		self.copy()
		script = self.install_dir / "cirdan.py"
		if not script.is_file():
			Console.info(f"Note: {script} not found after copy — check the source tree")
		try:
			self.offer_desktop_entry()
		except Exception as ex:
			Console.error(f"Could not create desktop entry: {ex}")

if __name__ == "__main__":
	try:
		LinInstaller.from_argv(argv[1:]).run()
	except Exception as ex:
		raise SystemExit(str(ex)) from ex
	exit(0)
