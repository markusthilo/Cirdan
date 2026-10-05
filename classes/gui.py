#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import perf_counter
from tkinter import Tk, PhotoImage, StringVar, BooleanVar
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror
from tkinter.filedialog import askdirectory, asksaveasfilename
from idlelib.tooltip import Hovertip
from classes.todo import ToDo
from classes.logger import Logger as Log
from classes.path import Path
from classes.update import Update
from classes.sendmail import SendMail
from classes.checksourcethread import CheckSourceThread
from classes.workthread import WorkThread
from classes.checkdstthread import CheckDstThread
from classes.tododialog import ToDoDialog

class Gui(Tk):
	'''GUI look and feel'''

	@staticmethod
	def startup_error(msg):
		'''Window showing startup error'''
		showerror(title='Cirdan - Critical error on startup', message=msg)

	def __init__(self, config, labels, settings, copy_tool, logger,
		user_log=None, source=None, todo=None, no_source_check=False):
		'''Open application window'''
		super().__init__()
		self.config = config
		self.labels = labels
		self.settings = settings
		self.log_path = user_log
		self.no_source_check = no_source_check
		self.logger = logger
		self._work_thread = None
		self._check_source_thread = None
		self._check_dst_thread = None
		try:
			self.copy = copy_tool
			self.title(f'{self.labels.title} v{self.labels.version}')
			self.rowconfigure(0, weight=1)
			self.columnconfigure(1, weight=1)
			self.rowconfigure(7, weight=1)
			self.iconphoto(True, PhotoImage(file=self.config.icon_path))
			self.protocol('WM_DELETE_WINDOW', self._quit_app)
			font = nametofont('TkTextFont').actual()
			font_family = font['family']
			font_size = font['size']
			self.min_size_x = font_size * self.config.gui['x_factor']
			self.min_size_y = font_size * self.config.gui['y_factor']
			self.minsize(self.min_size_x , self.min_size_y)
			self.geometry(f'{self.min_size_x}x{self.min_size_y}')
			self.resizable(True, True)
			self._pad = int(font_size * self.config.gui['pad_factor'])
			self._source_button = Button(self, text=self.labels.source_dir, command=self._select_source)
			self._source_button.grid(row=0, column=0, sticky='nw', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			Hovertip(self._source_button, self.labels.source_tip)
			self.sources = list()
			self._source_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._source_text.grid(row=0, column=1, sticky='nswe', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			self._source_text.configure(state='disabled')
			self._source_text.bind('<Key>', lambda dummy: 'break')
			self._delete_button = Button(self, text=self.labels.delete_source, command=self._delete_source)
			self._delete_button.grid(row=1, column=1, sticky='ne', padx=self._pad)#, pady=self._pad)
			Hovertip(self._delete_button, self.labels.delete_source_tip)
			label = Label(self, text=self.labels.destination)
			label.grid(row=2, column=0, sticky='w', padx=(2*self._pad, 0))
			Hovertip(label, self.labels.destination_tip)
			self.destination = StringVar()
			if len(self.config.reachable_dsts) > 1:
				OptionMenu(
					self,
					self.destination,
					self.settings.destination if self.settings.destination else self.labels.select_destination,
					*self.config.reachable_dsts,
					command = self._update_todo
				).grid(row=2, column=1, sticky='w', padx=self._pad)
			else:
				self.destination.set(next(iter(self.config.reachable_dsts)))
				Label(self, text=self.destination.get()).grid(row=2, column=1, columnspan=2, sticky='w', padx=self._pad)
			label = Label(self, text=f'{self.labels.todo}:')
			label.grid(row=3, column=0, sticky='w', padx=(2*self._pad, 0))
			Hovertip(label, self.labels.todo_tip)
			self._todo = StringVar()
			self._todo_menu = OptionMenu(self, self._todo)
			self._todo_menu.grid(row=3, column=1, sticky='w', padx=self._pad)
			Hovertip(self._todo_menu, self.labels.todo_tip)
			self._update_todo('_',)
			if todo and todo.key:
				self._todo.set(todo.key)
			self.todo = None
			frame = Frame(self)
			frame.grid(row=4, column=1, sticky='we', padx=self._pad)
			frame.columnconfigure(1, weight=1)
			self.mail_to = StringVar(value=self.settings.mail_to)
			self.mail_subject = StringVar(value=self.settings.mail_subject)
			try:
				use_mail = SendMail(self.config.mail).is_reachable()
			except:
				use_mail = False
			if use_mail:
				self.send_mail = BooleanVar(value=self.settings.sendmail)
				button = Checkbutton(frame, text=f'{self.labels.sendmail_button}:', variable=self.send_mail)
				button.grid(row=0, column=0, sticky='w', padx=(0, self._pad))
				Hovertip(button, self.labels.sendmail_tip)
				entry = Entry(frame, textvariable=self.mail_to)
				entry.grid(row=0, column=1, sticky='we')
				Hovertip(entry, self.labels.address_tip)
				label = Label(frame, text=f'@{self.config.domain}')
				label.grid(row=0, column=2, sticky='w')
				Hovertip(label, self.labels.address_tip)
				label = Label(frame, text=f'{self.labels.mail_subject}:')
				label.grid(row=1, column=0, sticky='e', padx=(0, self._pad))
				Hovertip(label, self.labels.mail_subject_tip)
				entry = Entry(frame, textvariable=self.mail_subject)
				entry.grid(row=1, column=1, columnspan=2, sticky='we')
				Hovertip(entry, self.labels.mail_subject_tip)
			else:
				self.send_mail = BooleanVar(value=False)
			frame = Frame(self)
			frame.grid(row=5, column=1, sticky='we', padx=self._pad)
			self.write_log = BooleanVar(value=bool(self.log_path))
			button = Checkbutton(frame, text=self.labels.log_button, variable=self.write_log, comman=self._select_log)
			button.pack(side='right', padx=self._pad)
			Hovertip(button, self.labels.log_tip)
			frame = Frame(self)
			frame.grid(row=6, column=1, sticky='we', padx=self._pad)
			self._create_todo_button = Button(frame, text=self.labels.create_todo, command=self._create_todo)
			self._create_todo_button.pack(side='left', padx=(0, self._pad))
			Hovertip(self._create_todo_button, self.labels.create_todo_tip)
			self._exec_button = Button(frame, text=self.labels.start_button, command=self._execute)
			self._exec_button.pack(side='right', padx=self._pad)
			Hovertip(self._exec_button, self.labels.start_tip)
			self._info_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._info_text.grid(row=7, column=0, columnspan=2, sticky='nsew',
				ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			self._info_text.bind('<Key>', lambda dummy: 'break')
			self._info_text.configure(state='disabled')
			self._last_echo = 0
			self._info_fg = self._info_text.cget('foreground')
			self._info_bg = self._info_text.cget('background')
			self._info_newline = True
			self.logger.set_echo(self.echo)
			self._info_label = Label(self)
			self._info_label.grid(row=8, column=0, sticky='w', padx=self._pad, pady=self._pad)
			self._label_fg = self._info_label.cget('foreground')
			self._label_bg = self._info_label.cget('background')
			self._quit_button = Button(self, text=self.labels.quit, command=self._quit_app)
			self._quit_button.grid(row=8, column=1, sticky='e', padx=self._pad, pady=self._pad)
			if True or not self.config.app_path.resolve().drive.startswith('\\\\'):	# check for updates
				update = Update(self.labels.version, self.config.update_path)
				if update.new_version and askyesno(
					title = self.labels.update_title.replace('#', update.new_version),
					message = self.labels.update_message,
					default = 'no'
				):
					try:
						update.download(self.config.app_path)
						self.destroy()
						return
					except:
						msg = Log.error()
						showerror(parent=self, title=self.labels.error, message=f'{self.labels.update_error}:\n{msg}')
			self._init_warning()
			if source:
				self._check_source_thread = CheckSourceThread(Path(source).resolve(), self)
				self._check_source_thread.start()
		except:
			msg = self.logger.crash()
			showerror(title=self.labels.error, message=msg)
			self.destroy()

	def _update_todo(self, *_):
		'''Change todo menu when changing destination'''
		try:
			todo_options = list(self.config.todo[self.config.destinations[self.destination.get()]['todo']].keys())
		except KeyError:
			self._todo_menu.set_menu(self.labels.select_destination_first)
		else:
			self._todo_menu.set_menu(self.labels.select_todo, *todo_options)

	def _create_todo(self):
		'''Check destination to open todo dialog'''
		if self.destination.get() not in self.config.destinations:
			showerror(title=self.labels.error, message=self.labels.select_destination_first)
			return
		self._get_settings()
		self._clear_info()
		self._disable_buttons()
		self._check_dst_thread = CheckDstThread(self)
		self._check_dst_thread.start()

	def abort_no_subdirs(self):
		'''Show error when no suitable subdirectory exists, then close'''
		showerror(title=self.labels.error, message=self.labels.no_sub_dirs_todo)
		self._enable_buttons()
		self._check_dst_thread = None

	def open_todo_dialog(self, destination):
		'''Open todo dialog'''
		dialog = ToDoDialog(self, destination)
		if dialog.winfo_exists():
			dialog.wait_window()
		self._enable_buttons()
		self._check_dst_thread = None

	def _select_source(self):
		'''Select directory to add into field'''
		if source := askdirectory(title=self.labels.select_dir, mustexist=True):
			source = Path(source).resolve()
			if source in self.sources:
				showerror(title=self.labels.error, message=self.labels.already_added.replace('#', f'{source}'))
				return
			self._disable_buttons()
			self._check_source_thread = CheckSourceThread(source, self)
			self._check_source_thread.start()

	def add_source(self, source):
		'''Run this after adding source'''
		self._check_source_thread = None
		self._clear_info()
		self._source_text.configure(state='normal')
		self._source_text.insert('end', f'{source}\n')
		self._source_text.configure(state='disabled')
		self._enable_buttons()
		self.sources.append(source)
		Log.info(self.labels.added_source.replace('#', f'{source}'))

	def abort_source_check(self):
		'''Run this after checking source and not adding it'''
		self._check_source_thread = None
		self._enable_buttons()
		Log.info(self.labels.aborted_source_check)

	def _delete_source(self):
		'''Delete last source directory from list'''
		if self.sources:
			self.sources.pop()
			self._source_text.configure(state='normal')
			self._source_text.delete('end-2l', 'end-1l')
			self._source_text.configure(state='disabled')

	def _clear_source_text(self):
		'''Clear source list'''
		self._source_text.configure(state='normal')
		self._source_text.delete('1.0', 'end')
		self._source_text.configure(state='disabled')
		self.sources = list()

	def _select_log(self):
		'''Select directory'''
		if self.write_log.get():
			defaultextension = Path(self.config.log_name).suffix.lstrip('.')
			filename = asksaveasfilename(
				title = self.labels.logfile,
				filetypes = (
					(f'{self.labels.logfile} (*.{defaultextension})', f'*.{defaultextension}'),
					(self.labels.allfiles, '*.*')
				),
				defaultextension = defaultextension,
				confirmoverwrite = True
			)
			if filename:
				self.log_path = Path(filename)
			else:
				self.write_log.set(False)
				self.log_path = None

	def echo(self, *args, end=None):
		'''Write message to info field (ScrolledText)'''
		last_echo = self._last_echo
		self._last_echo = int(perf_counter() * 10 )
		if end == '\r' and last_echo == self._last_echo:
			return
		msg = ' '.join(f'{arg}' for arg in args)
		self._info_text.configure(state='normal')
		if not self._info_newline:
			self._info_text.delete('end-2l', 'end-1l')
		self._info_text.insert('end', f'{msg}\n')
		self._info_text.configure(state='disabled')
		if self._info_newline:
			self._info_text.yview('end')
		self._info_newline = end != '\r'

	def _clear_info(self):
		'''Clear info text'''
		self._info_text.configure(state='normal')
		self._info_text.delete('1.0', 'end')
		self._info_text.configure(state='disabled')
		self._info_text.configure(foreground=self._info_fg, background=self._info_bg)
		self._warning_state = 'stop'

	def _disable_buttons(self):
		'''Disable source selector and start button'''
		self._source_button.configure(state='disabled')
		self._exec_button.configure(state='disabled')
		self._create_todo_button.configure(state='disabled')

	def _enable_buttons(self):
		'''Enable source selector and start button'''
		self._source_button.configure(state='normal')
		self._exec_button.configure(state='normal')
		self._create_todo_button.configure(state='normal')

	def _get_settings(self):
		'''Get settings from GUI'''
		self.settings.destination = self.destination.get()
		self.settings.sendmail = self.send_mail.get()
		self.settings.mail_to = self.mail_to.get()
		self.settings.mail_subject = self.mail_subject.get()

	def _save_settings(self):
		'''Get settings from GUI and save to JSON file'''
		self._get_settings()
		try:
			self.settings.save()
			Log.debug('Saved settings')
		except:
			Log.error()

	def _execute(self):
		'''Start copy process / worker'''
		self._get_settings()
		if not self.sources:
			showerror(title=self.labels.error, message=self.labels.missing_source)
			return
		if self.settings.sendmail and not self.settings.mail_to:
			showerror(title=self.labels.error, message=self.labels.missing_name)
			return
		if not self.settings.destination in self.config.destinations:
			showerror(
				title = self.labels.error,
				message = self.labels.bad_destination.replace('#', f'{self.settings.destination}')
			)
			return
		todo = self._todo.get()
		if todo == self.labels.select_todo:
			showerror(title=self.labels.error, message=self.labels.missing_todo_msg)
			return
		self.todo = ToDo(self._todo.get(), self.settings, self.config)
		self._save_settings()
		self._disable_buttons()
		self._clear_info()
		self._work_thread = WorkThread(self)
		self._work_thread.start()

	def _init_warning(self):
		'''Init warning functionality'''
		self._warning_state = 'disabled'
		self._warning()

	def _warning(self):
		'''Show flashing warning'''
		if self._warning_state == 'enable':
			self._info_label.configure(text=self.labels.warning)
			self._warning_state = '1'
		if self._warning_state == '1':
			self._info_label.configure(foreground=self.config.gui['red_fg'], background=self.config.gui['red_bg'])
			self._warning_state = '2'
		elif self._warning_state == '2':
			self._info_label.configure(foreground=self._label_fg, background=self._label_bg)
			self._warning_state = '1'
		elif self._warning_state != 'disabled':
			self._info_label.configure(text= '', foreground=self._label_fg, background=self._label_bg)
			self._warning_state = 'disabled'
		self.after(500, self._warning)

	def finished(self, errors):
		'''Run this when worker has finished'''
		self._work_thread = None
		self._enable_buttons()
		if errors is None:
			Log.info(self.labels.worker_killed)
			return
		self._clear_source_text()
		self.write_log.set(False)
		self.log_path = None
		if errors:
			self._info_text.configure(foreground=self.config.gui['red_fg'], background=self.config.gui['red_bg'])
			self._warning_state = 'enable'
			msg = f'{self.labels.problems}:'
			if len(errors) in (1, 2, 3):
				for error in errors:
					msg += f'\n\n{error}'
			elif errors:
				msg += f'\n\n{errors[0]}\n\n{errors[1]}\n\n{self.labels.more_problems.replace("#", f"{len(errors)-2}")}'
			showerror(title=self.labels.warning, message=msg)
		else:
			self._info_text.configure(foreground=self.config.gui['green_fg'], background=self.config.gui['green_bg'])

	def quit_app(self):
		'''Save settings end close application window'''
		self._save_settings()
		Log.debug('Quitting application')
		self.destroy()

	def _quit_app(self):
		'''Quit app, ask if copy process is running'''
		if self._work_thread:
			if not askyesno(title=self.labels.warning, message=self.labels.running_warning):
				return
			Log.info(self.labels.killing_running)
			try:
				self._work_thread.kill()
			except:
				pass
		elif self._check_source_thread:
			try:
				self._check_source_thread.kill()
			except:
				pass
		elif self._check_dst_thread:
			try:
				self._check_dst_thread.kill()
			except:
				pass
		else:
			self.quit_app()
