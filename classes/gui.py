#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import perf_counter
from threading import current_thread, main_thread
from collections.abc import Callable
from tkinter import Tk, PhotoImage, StringVar, BooleanVar, TclError
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu, Style, Treeview, Scrollbar
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror, showwarning, showinfo
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.simpledialog import askstring
from idlelib.tooltip import Hovertip
from classes.logger import Logger as Log
from classes.path import Path
from classes.update import Update
from classes.sendmail import SendMail
from classes.threads import InsertSrcDirThread, InsertSourcesThread,WorkThread
from classes.tododialog import ToDoDialog
from classes.messagedialog import prepare_message_parent
from classes.source import Source
from classes.destination import Destination
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

	def prepare_dialog(self) -> None:
		"""Map this window so the next message box stays in front of it"""
		prepare_message_parent(self)

	def _style_option_menus(self) -> None:
		"""Left-align OptionMenu text and draw the same border as a button"""
		style = Style(self)
		style.configure(
			"TMenubutton",
			anchor="w",
			relief="raised",
			borderwidth=1,
			padding=(0,0) 	#(self._pad, self._pad),
		)
		style.map("TMenubutton", relief=[("pressed", "sunken")])
		if self.settings.system == "Windows":
			self._style_windows_option_border(style)
			return

		def restyle(elements: list) -> list:
			styled = []
			for name, options in elements:
				options = dict(options)
				element = str(name)
				if element.endswith(".border"):
					element = "Button.border"
					options["sticky"] = "nswe"
					options["border"] = "1"
				if element.endswith("label"):
					options["side"] = "left"
					options["sticky"] = "w"
				children = options.get("children")
				if children:
					options["children"] = restyle(children)
				styled.append((element, options))
			return styled

		style.layout("TMenubutton", restyle(style.layout("TMenubutton")))

	def _style_windows_option_border(self, style: Style) -> None:
		"""Windows themes omit the OptionMenu border, so paint one explicitly"""
		try:
			style.element_create("Cirdan.Menubutton.border", "from", "clam", "border")
		except TclError:
			pass
		arrow = "Menubutton.indicator"
		for name in ("Menubutton.dropdown", "Menubutton.indicator"):
			try:
				style.element_options(name)
			except TclError:
				continue
			arrow = name
			break
		background = style.lookup(".", "background") or "SystemButtonFace"
		style.configure(
			"TMenubutton",
			background=background,
			bordercolor="SystemButtonShadow",
			lightcolor="SystemButtonHighlight",
			darkcolor="SystemButtonShadow",
		)
		style.layout("TMenubutton", [(
			"Cirdan.Menubutton.border", {
				"sticky": "nswe",
				"border": "1",
				"children": [(
					"Menubutton.focus", {
						"sticky": "nswe",
						"children": [
							(arrow, {"side": "right", "sticky": "ns"}),
							("Menubutton.padding", {
								"expand": "1",
								"sticky": "nswe",
								"children": [(
									"Menubutton.label",
									{"side": "left", "sticky": "w"},
								)],
							}),
						],
					},
				)],
			},
		)])

	def __init__(self, settings: Settings, logger: Log, sources: list[Path] = list[Path]()
	) -> None:
		"""Open application window"""
		super().__init__()
		self.settings = settings
		self.labels = self.settings.labels
		self.logger = logger
		self.source = None
		self._file_types = tuple[str, str]((tname, f"*{stem}") for stem, tname in (
				self.settings.source_sub_filetypes | {".*": "All Files"}
			).items()
		)
		self._todo_dialog: ToDoDialog | None = None
		self._work_thread: WorkThread | None = None
		self.source_thread: InsertSrcDirThread | None = None
		self.log_path: Path | None = self.settings.user_log
		try:
			self.title(f"{self.labels.title} v{self.settings.version}")
			self.rowconfigure(0, weight=1)
			self.rowconfigure(6, weight=20)
			self.columnconfigure(1, weight=1)
			self.iconphoto(True, PhotoImage(file=self.settings.icon_path))
			self.protocol("WM_DELETE_WINDOW", self._quit_app)
			font = nametofont("TkTextFont").actual()
			font_family = font["family"]
			font_size = font["size"]
			self.min_size_x = font_size * self.settings.gui["x_factor"]
			self.min_size_y = font_size * self.settings.gui["y_factor"]
			self.minsize(self.min_size_x , self.min_size_y)
			self.settings.gui_geometry = self.settings.gui_geometry or f"{self.min_size_x}x{self.min_size_y}"
			self.geometry(self.settings.gui_geometry)
			self.resizable(True, True)
			self._pad = int(font_size * self.settings.gui["pad_factor"])
			self._style_option_menus()
			### Source ###
			frame = Frame(self)
			frame.grid(row=0, column=0, sticky="nw", padx=self._pad, pady=(self._pad, 0))
			Label(frame, text=self.labels.add).pack(pady=(0, self._pad))
			self._add_dir_button = Button(frame, text=self.labels.dir, command=self._add_dir)
			self._add_dir_button.pack(fill="x", pady=(0, self._pad))
			Hovertip(self._add_dir_button, self.labels.add_dir_tip)
			self._add_file_button = Button(frame, text=self.labels.file, command=self._add_file)
			self._add_file_button.pack(fill="x", pady=(0, self._pad))
			Hovertip(self._add_file_button, self.labels.add_file_tip)
			frame = Frame(self)
			frame.grid(row=0, column=1, sticky="nswe", padx=self._pad, pady=self._pad)
			self._source_tree = Treeview(frame, show="tree headings", columns=("size", "files"), selectmode="browse")
			self._source_tree.heading("#0", text=self.labels.source_dir, anchor="w")
			self._source_tree.heading("size", text="Size", anchor="w")
			self._source_tree.heading("files", text="Files", anchor="w")
			self._source_tree.column("size", anchor="e", width=font_size * 16,stretch=False)
			self._source_tree.column("files", anchor="e", width=font_size * 12, stretch=False)
			self._source_tree.bind("<<TreeviewClose>>", lambda event: self._source_tree.item(self._source_tree.focus(), open=True))
			self._source_tree.bind('<Button-2>', self._right_click)
			self._source_tree.bind('<Button-3>', self._right_click)
			self._source_tree.pack(side='left', fill='both', expand=True)
			vsb = Scrollbar(frame, orient='vertical', command=self._source_tree.yview)
			vsb.pack(side='right', fill='y')
			self._source_tree.configure(yscrollcommand=vsb.set)
			frame = Frame(self)
			frame.grid(row=1, column=1, sticky="ne", padx=self._pad)
			self._set_top_dir_name_button = Button(frame, text=self.labels.top_name, command=self._set_top_dir_name)
			self._set_top_dir_name_button.pack(side="left", padx=self._pad)
			Hovertip(self._set_top_dir_name_button, self.labels.set_top_dir_name_tip)
			self._delete_button = Button(frame, text=self.labels.delete_source, command=self._delete_button_pressed, state="disabled")
			self._delete_button.pack(side="right", padx=self._pad)
			Hovertip(self._delete_button, self.labels.delete_source_tip)
			### Destination ###
			label = Label(self, text=f"{self.labels.destination}:")
			label.grid(row=2, column=0, sticky="w", padx=(2*self._pad, 0), pady=self._pad)
			Hovertip(label, self.labels.destination_tip)
			self._destination_name = StringVar(value=self.settings.destination_name)
			if self.settings.destination_arg_set or len(self.settings.accessible_destinations)== 1:
				Label(self, text=self.settings.destination_name).grid(row=2, column=1, columnspan=2, sticky="w", padx=self._pad)
			elif self.settings.destination_name in self.settings.accessible_destinations:
				OptionMenu(
					self,
					self._destination_name,
					self.settings.destination_name,
					*self.settings.accessible_destinations.keys(),
					command=self._destination_selected
				).grid(row=2, column=1, sticky="ew", padx=self._pad)
			else:
				OptionMenu(
					self,
					self._destination_name,
					self.labels.select_destination,
					*self.settings.accessible_destinations.keys(),
					command=self._destination_selected
				).grid(row=2, column=1, sticky="ew", padx=self._pad)
			### Todo ###
			label = Label(self, text=f"{self.labels.todo}:")
			label.grid(row=3, column=0, sticky="w", padx=(2*self._pad, 0), pady=(0, self._pad))
			Hovertip(label, self.labels.todo_tip)
			frame = Frame(self)
			frame.grid(row=3, column=1, sticky="ew", padx=self._pad)
			todo, do_something = self.settings.get_todo()
			self._todo = StringVar(value=todo)
			self._todo_boolean = BooleanVar(value=do_something)
			button = Checkbutton(frame, text="\u2194 ", variable=self._todo_boolean, command=self._toggle_todo)
			button.pack(side="left")
			self._todo_menu = OptionMenu(frame, self._todo, command=self._todo_selected)
			self._todo_menu.pack(side="left", expand=True, fill="x")
			Hovertip(frame, self.labels.todo_tip)
			if todo:
					self._todo_menu.set_menu(todo, *self.settings.destination_todos.keys())
			elif self.settings.destination_name:
					self._todo_menu.set_menu(self.labels.select_todo, *self.settings.destination_todos.keys())
			else:
				self._todo_menu.set_menu(self.labels.select_destination_first)
			### Mail ###
			frame = Frame(self)
			frame.grid(row=4, column=1, sticky="we", padx=self._pad)
			frame.columnconfigure(1, weight=1)
			self._mail_to = StringVar(value=self.settings.mail_to)
			self._mail_subject = StringVar(value=self.settings.mail_subject)
			try:
				use_mail = SendMail(self.settings.mail).is_reachable()
			except Exception:
				use_mail = False
			if use_mail:
				self._send_mail = BooleanVar(value=self.settings.sendmail)
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
				self._send_mail = BooleanVar(value=False)
			### Start button and log checkbox ###
			self._info_label = Label(self)
			self._info_label.grid(row=5, column=0, sticky="sw", padx=self._pad, pady=(0, self._pad))
			self._label_fg = self._info_label.cget("foreground")
			self._label_bg = self._info_label.cget("background")
			frame = Frame(self)
			frame.grid(row=5, column=1, sticky="nswe", padx=self._pad, pady=(0, self._pad))
			frame.columnconfigure(1, weight=1)
			self.write_log = BooleanVar(value=bool(self.settings.user_log))
			button = Checkbutton(frame, text=self.labels.log_button, variable=self.write_log, command=self._select_log)
			button.grid(row=0, column=0, sticky="nw", padx=(0, self._pad))
			Hovertip(button, self.labels.log_tip)
			style = Style(self)
			style.configure("Execute.TButton", font=(font_family, font_size * 2))
			self._exec_button = Button(frame, text=self.labels.start_button, style="Execute.TButton", command=self._execute, state="disabled")
			self._exec_button.grid(row=0, column=1, sticky="ew", padx=(self._pad, 0))
			Hovertip(self._exec_button, self.labels.start_tip)
			### Info text ###
			self._info_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._info_text.grid(row=6, column=0, columnspan=2, sticky="nsew",
				ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=(0, self._pad))
			self._info_text.bind("<Key>", lambda dummy: "break")
			self._info_text.configure(state="disabled")
			self._last_echo = 0
			self._info_fg = self._info_text.cget("foreground")
			self._info_bg = self._info_text.cget("background")
			self._info_newline = True
			self.logger.set_echo(self.echo)
			### Todo button and quit button ###
			frame = Frame(self)
			frame.grid(row=7, column=0, columnspan=2, sticky="we", padx=self._pad, pady=(0, self._pad))
			self._create_todo_button = Button(frame, text=self.labels.create_todo, command=self._open_todo_window)
			self._create_todo_button.pack(side="left", padx=(self._pad))
			Hovertip(self._create_todo_button, self.labels.create_todo_tip)
			self._quit_button = Button(frame, text=self.labels.quit, command=self._quit_app, state="disabled")
			self._quit_button.pack(side="right", padx=(0, self._pad))
			update = Update(self.settings.version, self.settings.update_path, self.settings.app_path)
			### Update check ###
			if update.new_version is not None:
				msg = self.labels.update_info.replace("#1", f"{update.new_version}").replace("#2", f"{self.settings.update_path}")
				self.prepare_dialog()
				if update.installer_cmd is None:
					showinfo(parent=self, title=self.labels.update_title, message=msg)
				else:
					if askyesno(
						parent=self,
						title=self.labels.update_title,
						message=msg + "\n\n" + self.labels.update_question,
						default="no"
					):
						try:
							update.install()
							self.destroy()
							return
						except Exception:
							msg = Log.error()
							self.prepare_dialog()
							showerror(parent=self, title=self.labels.error, message=f"{self.labels.update_error}:\n{msg}")
			########################################################
			if len(self.settings.accessible_destinations) < 1:
				raise RuntimeError(self.labels.no_reachable_destination)
			if sources:
				try:
					thread = InsertSourcesThread(self, sources)
				except:
					Log.error(self.labels.error_inserting_source.replace("#", "/".join(str(source) for source in sources)))
				else:
					thread.start()
			self._init_warning()
		except Exception:
			msg = self.logger.crash()
			self.prepare_dialog()
			showerror(parent=self, title=self.labels.error, message=msg)
			self.destroy()

	def gen_source_tree(self):
		'''Generate Treeview for Source'''
		self._source_tree.delete(*self._source_tree.get_children())
		if not self.source or self.source.is_empty():
			self._delete_button.configure(state="disabled")
			self._exec_button.configure(state="disabled")
			return
		self._delete_button.configure(state="normal")
		if self.source.name and self.source.sub_dirs:
			self._exec_button.configure(state="normal")
		else:
			self._exec_button.configure(state="disabled")
		self._source_tree.insert("", 0,
			text = self.source.name or self.labels.no_top_dir,
			values = (self.source.size, self.source.file_cnt),
			iid = "top",
			open = True
		)
		for name in self.source.get_sub_dir_list():
			self._source_tree.insert("top", "end",
				text = f"\U0001F5C0 {name}",
				values = (self.source.sub_dirs[name]["size"], self.source.sub_dirs[name]["files"]),
				iid = f"dir:{name}"
			)
		for name in self.source.get_sub_file_list():
			self._source_tree.insert("top", "end",
				text = f"\U0001F5C5 {name}",
				values = (self.source.sub_files[name]["size"]),
				iid = f"file:{name}"
			)

	def _add_dir(self) -> None:
		"""Add directory to source"""
		if self.source_thread and self.source_thread.is_alive():
			return
		self.prepare_dialog()
		if directory := askdirectory(title=self.labels.select_dir, mustexist=True):
			try:
				self.source_thread = InsertSrcDirThread(self, directory, self.gen_source_tree)
			except ValueError as ex:
				showerror(parent=self, title=self.labels.error, message=str(ex))
				return
			self.source_thread.start()

	def _add_file(self) -> None:
		"""Add file to source"""
		self.prepare_dialog()
		if filenames := askopenfilename(title=self.labels.select_file, multiple=True, filetypes=self._file_types):
			if not self.source:
				self.source = Source(self.settings)
			for filename in filenames:
				if sub_file := self.source.sub_file(filename):
					self.source.add_sub_file(sub_file)
				else:
					self.prepare_dialog()
					if askyesno(
						parent=self, title=self.labels.warning, message=self.labels.bad_file.replace("#", filename)
					) and askyesno(parent=self, title=self.labels.warning, message=self.labels.are_you_sure):
						self.source.add_sub_file(filename)
					else:
						continue
				self.echo(self.labels.added_file.replace("#", str(sub_file)))
			if self.source.is_empty():
				self.source = None
			else:
				self.gen_source_tree()

	def _delete_sub_item(self, row_id: str) -> None:
		"""Delete source"""
		if row_id.startswith("dir:"):
			self.prepare_dialog()
			if not askyesno(parent=self, title=self.labels.warning, message=self.labels.confirm_delete_sub_dir):
				return
			del self.source.sub_dirs[row_id[4:]]
			self.gen_source_tree()
		elif row_id.startswith("file:"):
			self.prepare_dialog()
			if not askyesno(parent=self, title=self.labels.warning, message=self.labels.confirm_delete_sub_file):
				return
			del self.source.sub_files[row_id[5:]]
			self.gen_source_tree()

	def _set_top_dir_name(self) -> None:
		"""Set top directory name"""
		self.prepare_dialog()
		if self.source and self.source.name:
			if not askyesno(parent=self, title=self.labels.warning, message=self.labels.sure_to_change_top):
				return
		else:
			self.source = Source(self.settings)
		input_string = askstring(parent=self, title=self.labels.warning, prompt=self.labels.top_name)
		if name := self.source.top_name(input_string):
			self.source.set_name(name)
		else:
			showwarning(parent=self, title=self.labels.warning, message=self.labels.not_a_valid_directory.replace("#", input_string))
			if not askyesno(parent=self, title=self.labels.warning, message=self.labels.ignore_warning):
				return
			self.source.set_name(input_string)
		self.gen_source_tree()

	def _right_click(self, event) -> None:
		"""Right click on source tree"""
		if row_id := self._source_tree.identify_row(event.y):
			self._source_tree.selection_set(row_id)
			self._source_tree.focus(row_id)
			if row_id == "top":
				self._set_top_dir_name()
			else:
				self._delete_sub_item(row_id)

	def _delete_button_pressed(self) -> None:
		"""Delete last source directory from list"""
		row_id = self._source_tree.focus()
		if not row_id or row_id == "top":
			self.prepare_dialog()
			if askyesno(parent=self, title=self.labels.warning, message=self.labels.confirm_delete_full_source):
				self.source = None
				self.gen_source_tree()
		else:
			self._delete_sub_item(row_id)

	def _destination_selected(self, *_: object) -> None:
		"""Set destination and change todo menu when changing destination"""
		destination_name = self._destination_name.get()
		if destination_name in self.settings.accessible_destinations:
			self.settings.set_destination(destination_name)
			self._todo_boolean.set(False)
			self._todo_menu.set_menu(self.labels.select_todo, *self.settings.destination_todos.keys())

	def _todo_selected(self, *_: object) -> None:
		"""Set selected todo"""
		if self.settings.destination_name:
			self.settings.set_todo(self._todo.get())
			todo, do_something = self.settings.get_todo()
			self._todo_menu.set_menu(todo, *self.settings.destination_todos.keys())
			self._todo_boolean.set(do_something)

	def _toggle_todo(self) -> None:
		"""Toggle todo checkbox"""
		checked = self._todo_boolean.get()
		self._todo_boolean.set(False)
		if self.settings.destination_name:
			if checked:
				self._todo_menu.tk.call("ttk::menubutton::Popdown", self._todo_menu)
			else:
				self.settings.set_todo(self.settings.destination_do_nothing)
				self._todo_menu.set_menu(self.settings.destination_do_nothing, *self.settings.destination_todos.keys())

	def _open_todo_window(self) -> None:
		"""Check destination to open todo dialog"""
		if self._todo_dialog and self._todo_dialog.is_alive():
			return
		self.prepare_dialog()
		if not self.settings.destination_name:
			showerror(parent=self, title=self.labels.error, message=self.labels.select_destination_first)
			return
		if not self.settings.accessible_destinations:
			showerror(parent=self, title=self.labels.error, message=self.labels.no_sub_dirs_todo)
			return
		destination = Destination(self.settings)
		if destination.check_sub_dirs():
			self.clear_info()
			self._disable_buttons()
			self._todo_dialog = ToDoDialog(self)
			self._todo_dialog.wait_window()
			print("todo dialog closed")
			self._todo_dialog = None
			self._enable_buttons()
		else:
			showinfo(parent=self, title=self.labels.info, message=self.labels.no_sub_dirs_todo)

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

	def create_todo(self, selected_path: Path, todo: dict) -> None:
		"""Create todo"""
		self._call_ui(self._create_todo, selected_path, todo)

	def _create_todo(self, selected_path: Path, todo: dict) -> None:
		"""Create todo"""
		self._todo_dialog.destroy()
		self._todo_dialog = None
		meta_content = todo.get("meta_content") or ""
		if "%p" in meta_content:
			counted_paths = self.settings.destination.count_paths(selected_path, self.echo) or {}
		else:
			counted_paths = {}
		try:
			self.settings.destination.delete_trigger(todo, selected_path)
			self.settings.destination.write_meta(todo, selected_path, counted_paths)
			self.settings.destination.write_trigger(todo, selected_path)
		except Exception:
			self.prepare_dialog()
			showerror(parent=self, title=self.labels.error, message=self.logger.error())
			return
		self.echo(self.labels.todo_created.replace('#1', f'{todo}').replace('#2', selected_path.name))
		self._quit_button.configure(state="normal")

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

	def clear_info(self) -> None:
		"""Clear info text"""
		self._info_text.configure(state="normal")
		self._info_text.delete("1.0", "end")
		self._info_text.configure(state="disabled")
		self._info_text.configure(foreground=self._info_fg, background=self._info_bg)
		self._warning_state = "stop"

	def _disable_buttons(self) -> None:
		"""Disable source selector and start button"""
		self._add_dir_button.configure(state="disabled")
		self._add_file_button.configure(state="disabled")
		self._set_top_dir_name_button.configure(state="disabled")
		self._exec_button.configure(state="disabled")
		self._create_todo_button.configure(state="disabled")

	def _enable_buttons(self) -> None:
		"""Enable source selector and start button"""
		self._add_dir_button.configure(state="normal")
		self._add_file_button.configure(state="normal")
		self._set_top_dir_name_button.configure(state="normal")
		self._exec_button.configure(state="normal")
		self._create_todo_button.configure(state="normal")
		self._quit_button.configure(state="normal")
		self.gen_source_tree()

	def _get_settings(self) -> None:
		"""Get settings from GUI"""
		self.settings.destination_name = self._destination_name.get()
		self.settings.sendmail = self._send_mail.get()
		self.settings.mail_to = self._mail_to.get()
		self.settings.mail_subject = self._mail_subject.get()

	def _save_settings(self) -> None:
		"""Get settings from GUI and save to JSON file"""
		self._get_settings()
		try:
			self.settings.save(gui_geometry=f"{self.winfo_width()}x{self.winfo_height()}")
			Log.debug("Saved settings")
		except Exception:
			Log.error()

	def _execute(self) -> None:
		"""Start copy process / worker"""
		self._get_settings()
		if self._work_thread and self._work_thread.is_alive():
			return
		self.prepare_dialog()
		if not self.source or self.source.is_empty():
			showerror(parent=self, title=self.labels.error, message=self.labels.missing_source)
			return
		if not self.settings.destination_name:
			showerror(
				parent=self,
				title=self.labels.error,
				message=self.labels.bad_destination.replace("#", f"{self.destination.get()}")
			)
			return
		if self.settings.sendmail and not self.settings.mail_to:
			showerror(parent=self, title=self.labels.error, message=self.labels.missing_name)
			return
		todo = self._todo.get()
		if not todo or todo == self.labels.select_todo:
			self.prepare_dialog()
			showerror(parent=self, title=self.labels.error, message=self.labels.missing_todo_msg)
			return
		self.settings.set_todo(todo)
		if not self.write_log.get():
			self.log_path = None
		try:
			self._work_thread = WorkThread(self)
		except:
			self.prepare_dialog()
			showerror(parent=self, title=self.labels.error, message=self.logger.error())
			return
		self.clear_info()
		self._save_settings()
		self._disable_buttons()
		self._work_thread.start()

	def _init_warning(self) -> None:
		"""Init warning functionality"""
		self._warning_state = "disabled"
		self._warning()

	def _warning(self) -> None:
		"""Show flashing warning"""
		if self._warning_state == "enable":
			self._info_label.configure(text=f"\u26A0 {self.labels.warning}")
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

	def finished(self, returncode: int | str) -> None:
		"""Run this when worker has finished (called from WorkThread)"""
		self._call_ui(self._finished, returncode)

	def _finished(self, returncode: int | str) -> None:
		self._work_thread = None
		self._enable_buttons()
		if returncode == "killed":
			Log.info(self.labels.worker_killed)
			return
		self.write_log.set(False)
		self.log_path = None
		if returncode:
			self._info_text.configure(foreground=self.settings.gui["red_fg"], background=self.settings.gui["red_bg"])
			self._warning_state = "enable"
			self.prepare_dialog()
			showerror(parent=self, title=self.labels.warning, message=f"{self.labels.problems}")
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
			self.prepare_dialog()
			if askyesno(parent=self, title=self.labels.warning, message=self.labels.running_warning):
				Log.info(self.labels.killing_running)
				try:
					self._work_thread.kill()
				except Exception:
					pass
			return
		if self.source_thread and self.source_thread.is_alive():
			self.prepare_dialog()
			if not askyesno(parent=self, title=self.labels.warning, message=self.labels.running_warning):
				return
			Log.info(self.labels.killing_running)
			try:
				self.source_thread.kill()
				self.source_thread.join(timeout=2)
			except Exception:
				pass
			self.source_thread = None
		self.quit_app()
