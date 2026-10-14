#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import perf_counter
from threading import current_thread, main_thread
from collections.abc import Callable
from tkinter import Tk, PhotoImage, StringVar, BooleanVar, TclError
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror
from tkinter.filedialog import askdirectory, asksaveasfilename
from idlelib.tooltip import Hovertip
from classes.logger import Logger as Log
from classes.path import Path
from classes.update import Update
from classes.sendmail import SendMail
from classes.checksourcethread import CheckSourceThread
from classes.workthread import WorkThread
from classes.tododialog import ToDoDialog
from classes.source import Source
from classes.settings import Settings

class Gui(Tk):
	"""GUI look and feel"""

	@staticmethod
	def startup_error(msg: str) -> None:
		"""Window showing startup error"""
		try:
			showerror(title="Cirdan - Critical error on startup", message=msg)
		except Exception:
			pass

	def __init__(self, settings: Settings, logger: Log, source: Path | None = None) -> None:
		"""Open application window"""
		super().__init__()
		self.settings = settings
		self.labels = self.settings.labels
		self.logger = logger
		self._todo_dialog: ToDoDialog | None = None
		self._work_thread: WorkThread | None = None
		self._check_source_thread: CheckSourceThread | None = None
		self.log_path: Path | None = self.settings.user_log
		try:
			self.title(f"{self.labels.title} v{self.settings.version}")
			self.rowconfigure(0, weight=1)
			self.columnconfigure(1, weight=1)
			self.rowconfigure(7, weight=1)
			self.iconphoto(True, PhotoImage(file=self.settings.icon_path))
			self.protocol("WM_DELETE_WINDOW", self._quit_app)
			font = nametofont("TkTextFont").actual()
			font_family = font["family"]
			font_size = font["size"]
			self.min_size_x = font_size * self.settings.gui["x_factor"]
			self.min_size_y = font_size * self.settings.gui["y_factor"]
			self.minsize(self.min_size_x , self.min_size_y)
			self.geometry(f"{self.min_size_x}x{self.min_size_y}")
			self.resizable(True, True)
			self._pad = int(font_size * self.settings.gui["pad_factor"])
			self._source_button = Button(self, text=self.labels.source_dir, command=self._select_source)
			self._source_button.grid(row=0, column=0, sticky="nw", ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			Hovertip(self._source_button, self.labels.source_tip)
			self.sources: list[Source] = list()
			self._source_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._source_text.grid(row=0, column=1, sticky="nswe", ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			self._source_text.configure(state="disabled")
			self._source_text.bind("<Key>", lambda dummy: "break")
			self._delete_button = Button(self, text=self.labels.delete_source, command=self._delete_source)
			self._delete_button.grid(row=1, column=1, sticky="ne", padx=self._pad)
			Hovertip(self._delete_button, self.labels.delete_source_tip)
			label = Label(self, text=self.labels.destination)
			label.grid(row=2, column=0, sticky="w", padx=(2*self._pad, 0))
			Hovertip(label, self.labels.destination_tip)
			self.destination = StringVar()
			selected_destination = (
				self.settings.destination.name if self.settings.destination else self.labels.select_destination
			)
			if len(self.settings.accessible_destinations) > 1:
				OptionMenu(
					self,
					self.destination,
					selected_destination,
					*self.settings.accessible_destinations.keys(),
					command=self._destination_selected
				).grid(row=2, column=1, sticky="ew", padx=self._pad)
			else:
				self.destination.set(
					self.settings.destination.name if self.settings.destination else ""
				)
				Label(
					self,
					text=self.settings.destination.name if self.settings.destination else self.labels.select_destination,
				).grid(row=2, column=1, columnspan=2, sticky="w", padx=self._pad)
			label = Label(self, text=f"{self.labels.todo}:")
			label.grid(row=3, column=0, sticky="w", padx=(2*self._pad, 0))
			Hovertip(label, self.labels.todo_tip)
			frame = Frame(self)
			frame.grid(row=3, column=1, sticky="ew", padx=self._pad)
			self._todo = StringVar()
			self._todo_boolean = BooleanVar()
			button = Checkbutton(frame, text="\u2194 ", variable=self._todo_boolean, command=self._toggle_todo)
			button.pack(side="left")
			self._todo_menu = OptionMenu(frame, self._todo, command=self._todo_selected)
			self._todo_menu.pack(side="left", expand=True, fill="x")
			Hovertip(frame, self.labels.todo_tip)
			self._destination_selected()
			frame = Frame(self)
			frame.grid(row=4, column=1, sticky="we", padx=self._pad)
			frame.columnconfigure(1, weight=1)
			self.mail_to = StringVar(value=self.settings.mail_to)
			self.mail_subject = StringVar(value=self.settings.mail_subject)
			try:
				use_mail = SendMail(self.settings.mail).is_reachable()
			except Exception:
				use_mail = False
			if use_mail:
				self.send_mail = BooleanVar(value=self.settings.sendmail)
				button = Checkbutton(frame, text=f"{self.labels.sendmail_button}:", variable=self.send_mail)
				button.grid(row=0, column=0, sticky="w", padx=(0, self._pad))
				Hovertip(button, self.labels.sendmail_tip)
				entry = Entry(frame, textvariable=self.mail_to)
				entry.grid(row=0, column=1, sticky="we")
				Hovertip(entry, self.labels.address_tip)
				label = Label(frame, text=f"@{self.settings.domain}")
				label.grid(row=0, column=2, sticky="w")
				Hovertip(label, self.labels.address_tip)
				label = Label(frame, text=f"{self.labels.mail_subject}:")
				label.grid(row=1, column=0, sticky="e", padx=(0, self._pad))
				Hovertip(label, self.labels.mail_subject_tip)
				entry = Entry(frame, textvariable=self.mail_subject)
				entry.grid(row=1, column=1, columnspan=2, sticky="we")
				Hovertip(entry, self.labels.mail_subject_tip)
			else:
				self.send_mail = BooleanVar(value=False)
			frame = Frame(self)
			frame.grid(row=5, column=1, sticky="we", padx=self._pad)
			self.write_log = BooleanVar(value=bool(self.settings.user_log))
			button = Checkbutton(frame, text=self.labels.log_button, variable=self.write_log, command=self._select_log)
			button.pack(side="right")
			Hovertip(button, self.labels.log_tip)
			frame = Frame(self)
			frame.grid(row=6, column=1, sticky="we", padx=self._pad)
			self._create_todo_button = Button(frame, text=self.labels.create_todo, command=self._open_todo_window)
			self._create_todo_button.pack(side="left", padx=(0, self._pad))
			Hovertip(self._create_todo_button, self.labels.create_todo_tip)
			self._exec_button = Button(frame, text=self.labels.start_button, command=self._execute)
			self._exec_button.pack(side="right")
			Hovertip(self._exec_button, self.labels.start_tip)
			self._info_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._info_text.grid(row=7, column=0, columnspan=2, sticky="nsew",
				ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			self._info_text.bind("<Key>", lambda dummy: "break")
			self._info_text.configure(state="disabled")
			self._last_echo = 0
			self._info_fg = self._info_text.cget("foreground")
			self._info_bg = self._info_text.cget("background")
			self._info_newline = True
			self.logger.set_echo(self.echo)
			self._info_label = Label(self)
			self._info_label.grid(row=8, column=0, sticky="w", padx=self._pad, pady=self._pad)
			self._label_fg = self._info_label.cget("foreground")
			self._label_bg = self._info_label.cget("background")
			self._quit_button = Button(self, text=self.labels.quit, command=self._quit_app)
			self._quit_button.grid(row=8, column=1, sticky="e", padx=self._pad, pady=self._pad)
			# Skip update check when running from a network share (UNC path)
			if not str(self.settings.app_path.resolve()).startswith("\\\\"):
				update = Update(self.settings.version, self.settings.update_path)
				if update.new_version and askyesno(
					title=self.labels.update_title.replace("#", update.new_version),
					message=self.labels.update_message,
					default="no"
				):
					try:
						update.download(self.settings.app_path)
						self.destroy()
						return
					except Exception:
						msg = Log.error()
						showerror(parent=self, title=self.labels.error, message=f"{self.labels.update_error}:\n{msg}")
			self._init_warning()
			if source:
				self._check_source_thread = CheckSourceThread(self, source)
				self._check_source_thread.start()
		except Exception:
			msg = self.logger.crash()
			showerror(title=self.labels.error, message=msg)
			self.destroy()

	def _destination_selected(self, *_: object) -> None:
		"""Set destination and change todo menu when changing destination"""
		destination = self.destination.get()
		if destination in self.settings.accessible_destinations:
			self.settings.set_destination(destination)
			self._todo.set(self.labels.select_todo)
			self._todo_menu.set_menu(self.labels.select_todo, *self.settings.destination.todos.keys())
		else:
			self.settings.set_destination(destination)
			self._todo_menu.set_menu(self.labels.select_destination_first)
		self._todo_boolean.set(False)

	def _todo_selected(self, *_: object) -> None:
		"""Set selected todo"""
		if not self.settings.destination:
			return
		todo = self._todo.get()
		if todo in self.settings.destination.todos:
			self.settings.set_todo(todo)
			self._todo_menu.set_menu(todo, *self.settings.destination.todos.keys())
			self._todo_boolean.set(bool(self.settings.destination.todos[todo]["do_something"]))
		else:
			self.settings.set_todo(None)
			self._todo_menu.set_menu(self.labels.select_todo, *self.settings.destination.todos.keys())
			self._todo_boolean.set(False)

	def _toggle_todo(self) -> None:
		"""Toggle todo checkbox"""
		if not self.settings.destination:
			self._todo_boolean.set(False)
			return
		if self._todo_boolean.get():
			self._todo_menu.tk.call("ttk::menubutton::Popdown", self._todo_menu)
		else:
			self._todo_menu.set_menu(self.settings.destination.do_nothing, *self.settings.destination.todos.keys())
			self._todo_boolean.set(False)

	def _open_todo_window(self) -> None:
		"""Check destination to open todo dialog"""
		if not self.settings.destination:
			showerror(title=self.labels.error, message=self.labels.select_destination_first)
			return
		sub_dir_paths = self.settings.destination.check_sub_dirs(self.settings.username)
		if not sub_dir_paths:
			showerror(title=self.labels.error, message=self.labels.no_sub_dirs_todo)
			return
		self._disable_buttons()
		self._todo_dialog = ToDoDialog(self)
		self._todo_dialog.wait_window()
		self._enable_buttons()
		self._todo_dialog = None

	def create_todo(self, selected_path: Path, todo: str) -> None:
		"""Create todo"""
		self._todo_dialog.destroy()
		self._todo_dialog = None
		meta_content = self.settings.destination.todos[todo].get("meta_content") or ""
		if "%p" in meta_content:
			counted_paths = self.settings.destination.count_paths(selected_path, self.echo) or {}
		else:
			counted_paths = {}
		try:
			self.settings.destination.delete_trigger(todo, selected_path)
			self.settings.destination.write_meta(todo, selected_path, counted_paths)
			self.settings.destination.write_trigger(todo, selected_path)
		except Exception:
			showerror(parent=self, title=self.labels.error, message=self.logger.error())
			return
		self.echo(self.labels.todo_created.replace('#1', f'{todo}').replace('#2', selected_path.name))

	def _select_source(self) -> None:
		"""Select directory to add into field"""
		if source := askdirectory(title=self.labels.select_dir, mustexist=True):
			source = Path(source).resolve()
			if any(source == item.path for item in self.sources):
				showerror(title=self.labels.error, message=self.labels.already_added.replace("#", f"{source}"))
				return
			self._disable_buttons()
			self._check_source_thread = CheckSourceThread(self, source)
			self._check_source_thread.start()

	def add_source(self, source: Source) -> None:
		"""Run this after adding source (called from CheckSourceThread)"""
		self._call_ui(self._add_source, source)

	def _add_source(self, source: Source) -> None:
		self._check_source_thread = None
		self._clear_info()
		self._source_text.configure(state="normal")
		self._source_text.insert("end", f"{source}\n")
		self._source_text.configure(state="disabled")
		self._enable_buttons()
		self.sources.append(source)
		Log.info(self.labels.added_source.replace("#", f"{source}"))

	def abort_source_check(self) -> None:
		"""Run this after checking source and not adding it (called from CheckSourceThread)"""
		self._call_ui(self._abort_source_check)

	def _abort_source_check(self) -> None:
		self._check_source_thread = None
		self._enable_buttons()
		Log.info(self.labels.aborted_source_check)

	def _delete_source(self) -> None:
		"""Delete last source directory from list"""
		if self.sources:
			self.sources.pop()
			self._source_text.configure(state="normal")
			self._source_text.delete("end-2l", "end-1l")
			self._source_text.configure(state="disabled")

	def _clear_source_text(self) -> None:
		"""Clear source list"""
		self._source_text.configure(state="normal")
		self._source_text.delete("1.0", "end")
		self._source_text.configure(state="disabled")
		self.sources = list()

	def _select_log(self) -> None:
		"""Select directory"""
		if self.write_log.get():
			defaultextension = Path(self.settings.log_name).suffix.lstrip(".")
			filename = asksaveasfilename(
				title=self.labels.logfile,
				filetypes=(
					(f"{self.labels.logfile} (*.{defaultextension})", f"*.{defaultextension}"),
					(self.labels.allfiles, "*.*")
				),
				defaultextension=defaultextension,
				confirmoverwrite=True
			)
			if filename:
				self.log_path = Path(filename)
			else:
				self.write_log.set(False)
				self.log_path = None
		else:
			self.log_path = None

	def _call_ui(self, fn: Callable[..., None], *args: object, **kwargs: object) -> None:
		"""Run a widget update on the Tk main thread"""
		def run() -> None:
			try:
				fn(*args, **kwargs)
			except TclError:
				pass
		try:
			if current_thread() is main_thread():
				run()
			else:
				self.after(0, run)
		except (RuntimeError, TclError):
			pass

	def echo(self, *args: object, end: str | None = None) -> None:
		"""Write message to info field (ScrolledText)"""
		last_echo = self._last_echo
		self._last_echo = int(perf_counter() * 10 )
		if end == "\r" and last_echo == self._last_echo:
			return
		msg = " ".join(f"{arg}" for arg in args)
		replace = not self._info_newline
		self._info_newline = end != "\r"
		self._call_ui(self._echo_ui, msg, replace)

	def _echo_ui(self, msg: str, replace: bool) -> None:
		"""Write to the info field (must run on the Tk thread)"""
		self._info_text.configure(state="normal")
		if replace:
			self._info_text.delete("end-2l", "end-1l")
		self._info_text.insert("end", f"{msg}\n")
		self._info_text.configure(state="disabled")
		if not replace:
			self._info_text.yview("end")

	def _clear_info(self) -> None:
		"""Clear info text"""
		self._info_text.configure(state="normal")
		self._info_text.delete("1.0", "end")
		self._info_text.configure(state="disabled")
		self._info_text.configure(foreground=self._info_fg, background=self._info_bg)
		self._warning_state = "stop"

	def _disable_buttons(self) -> None:
		"""Disable source selector and start button"""
		self._source_button.configure(state="disabled")
		self._exec_button.configure(state="disabled")
		self._create_todo_button.configure(state="disabled")

	def _enable_buttons(self) -> None:
		"""Enable source selector and start button"""
		self._source_button.configure(state="normal")
		self._exec_button.configure(state="normal")
		self._create_todo_button.configure(state="normal")

	def _get_settings(self) -> None:
		"""Get settings from GUI"""
		self.settings.set_destination(self.destination.get())
		self.settings.sendmail = self.send_mail.get()
		self.settings.mail_to = self.mail_to.get()
		self.settings.mail_subject = self.mail_subject.get()

	def _save_settings(self) -> None:
		"""Get settings from GUI and save to JSON file"""
		self._get_settings()
		try:
			self.settings.save()
			Log.debug("Saved settings")
		except Exception:
			Log.error()

	def _execute(self) -> None:
		"""Start copy process / worker"""
		self._get_settings()
		if self._work_thread and self._work_thread.is_alive():
			return
		if not self.sources:
			showerror(title=self.labels.error, message=self.labels.missing_source)
			return
		if self.settings.sendmail and not self.settings.mail_to:
			showerror(title=self.labels.error, message=self.labels.missing_name)
			return
		if not self.settings.destination:
			showerror(
				title=self.labels.error,
				message=self.labels.bad_destination.replace("#", f"{self.destination.get()}")
			)
			return
		todo = self._todo.get()
		if not todo or todo == self.labels.select_todo:
			showerror(title=self.labels.error, message=self.labels.missing_todo_msg)
			return
		self.settings.set_todo(todo)
		if not self.write_log.get():
			self.log_path = None
		self._save_settings()
		self._disable_buttons()
		self._clear_info()
		self._work_thread = WorkThread(self)
		self._work_thread.start()

	def _init_warning(self) -> None:
		"""Init warning functionality"""
		self._warning_state = "disabled"
		self._warning()

	def _warning(self) -> None:
		"""Show flashing warning"""
		if self._warning_state == "enable":
			self._info_label.configure(text=self.labels.warning)
			self._warning_state = "1"
		if self._warning_state == "1":
			self._info_label.configure(foreground=self.settings.gui["red_fg"], background=self.settings.gui["red_bg"])
			self._warning_state = "2"
		elif self._warning_state == "2":
			self._info_label.configure(foreground=self._label_fg, background=self._label_bg)
			self._warning_state = "1"
		elif self._warning_state != "disabled":
			self._info_label.configure(text="", foreground=self._label_fg, background=self._label_bg)
			self._warning_state = "disabled"
		self.after(500, self._warning)

	def finished(self, errors: list[str] | None) -> None:
		"""Run this when worker has finished (called from WorkThread)"""
		self._call_ui(self._finished, errors)

	def _finished(self, errors: list[str] | None) -> None:
		self._work_thread = None
		self._enable_buttons()
		if errors is None:
			Log.info(self.labels.worker_killed)
			return
		self._clear_source_text()
		self.write_log.set(False)
		self.log_path = None
		if errors:
			self._info_text.configure(foreground=self.settings.gui["red_fg"], background=self.settings.gui["red_bg"])
			self._warning_state = "enable"
			msg = f"{self.labels.problems}:"
			if len(errors) in (1, 2, 3):
				for error in errors:
					msg += f"\n\n{error}"
			elif errors:
				more = self.labels.more_problems.replace("#", f"{len(errors)-2}")
				msg += f"\n\n{errors[0]}\n\n{errors[1]}\n\n{more}"
			showerror(title=self.labels.warning, message=msg)
		else:
			self._info_text.configure(foreground=self.settings.gui["green_fg"], background=self.settings.gui["green_bg"])

	def quit_app(self) -> None:
		"""Save settings end close application window"""
		self._call_ui(self._quit_now)

	def _quit_now(self) -> None:
		self._save_settings()
		Log.debug("Quitting application")
		self.destroy()

	def _quit_app(self) -> None:
		"""Quit app; abort running worker without quitting, kill source check then quit"""
		if self._work_thread and self._work_thread.is_alive():
			if askyesno(title=self.labels.warning, message=self.labels.running_warning):
				Log.info(self.labels.killing_running)
				try:
					self._work_thread.kill()
				except Exception:
					pass
			return
		if self._check_source_thread and self._check_source_thread.is_alive():
			if not askyesno(title=self.labels.warning, message=self.labels.running_warning):
				return
			Log.info(self.labels.killing_running)
			try:
				self._check_source_thread.kill()
				self._check_source_thread.join(timeout=2)
			except Exception:
				pass
			self._check_source_thread = None
		self.quit_app()
