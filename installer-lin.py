#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import argv, exit
from subprocess import run, CompletedProcess, DEVNULL
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

class SudoCopy:
	"""Copy a source tree into an install directory with sudo cp -a"""

	def __init__(self, source: Path, destination: Path) -> None:
		self.source = Path(source).resolve()
		self.destination = Path(destination)
		if not self.source.is_dir():
			raise NotADirectoryError(f"Source is not a directory: {self.source}")

	def ensure_destination(self, echo: bool = True) -> None:
		"""Create the destination directory (and parents) if missing"""
		Sudo.run(["mkdir", "-p", str(self.destination)], echo=echo)

	def run(self) -> None:
		"""Create destination and copy source contents into it"""
		self.ensure_destination()
		# Trailing /. copies contents into destination (not a nested sourcedir/)
		Sudo.run(["cp", "-a", f"{self.source}/.", str(self.destination)])

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
	"""Install Cirdan with sudo cp and register a .desktop launcher"""

	DEFAULT_INSTALL_DIR = Path("/opt/Cirdan")
	DESKTOP_PATH = Path("/usr/share/applications/cirdan.desktop")

	def __init__(self, source: Path | str, destination: Path | str | None = None) -> None:
		self.source = Path(source)
		self.install_dir = Path(destination) if destination else self.DEFAULT_INSTALL_DIR
		self.desktop_path = self.DESKTOP_PATH

	@classmethod
	def from_argv(cls, args: list[str]) -> "LinInstaller":
		"""Build installer from CLI args; ask for destination if only source is given"""
		if len(args) == 1:
			source = Path(args[0])
			destination = Console.ask_path("Install directory", cls.DEFAULT_INSTALL_DIR)
		elif len(args) == 2:
			source = Path(args[0])
			destination = Path(args[1])
		else:
			raise SystemExit(
				f"Usage: {argv[0]} <sourcedir> [destinationdir]\n"
				f"  If destinationdir is omitted, you will be asked "
				f"(default: {cls.DEFAULT_INSTALL_DIR})"
			)
		return cls(source, destination)

	def ensure_destination(self) -> None:
		"""Create the install directory if it does not exist"""
		SudoCopy(self.source, self.install_dir).ensure_destination()

	def copy(self) -> None:
		"""Copy source tree into the install directory (creates destination if needed)"""
		SudoCopy(self.source, self.install_dir).run()

	def install_desktop_entry(self) -> Path:
		"""Create /usr/share/applications/cirdan.desktop"""
		path = DesktopEntry(self.install_dir, self.desktop_path).create()
		Console.info(f"Desktop entry created: {path}")
		return path

	def offer_desktop_entry(self) -> Path | None:
		"""Interactively offer the applications-menu launcher"""
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
