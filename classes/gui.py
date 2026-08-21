#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from threading import Thread, Event
from traceback import format_exc as get_exception
from time import perf_counter
from tkinter import Tk, PhotoImage, StringVar, BooleanVar
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror, showwarning, askyesnocancel
from tkinter.filedialog import askdirectory, asksaveasfilename
from idlelib.tooltip import Hovertip
from classes.source import Source
from classes.worker import Worker
from classes.regex import RegEx
from classes.logger import Logger as Log
from classes.path import Path
from classes.json import Json
from classes.update import Update
from classes.sendmail import SendMail
from classes.robocopy import RoboCopy

class CheckSourceThread(Thread):
	'''Thread that checks if a directory is a valid source'''

	def __init__(self, source_dir, gui):
		'''Pass source directory to add to GUI'''
		self._gui = gui
		self._source = Source(source_dir,
			max_path_len = None if self._gui.no_source_check else self._gui.config.max_path_length,
			whitelist = None if self._gui.no_source_check else self._gui.config.source_whitelist,
			blacklist = None if self._gui.no_source_check else self._gui.config.source_blacklist
		)
		super().__init__()
		self._kill_event = Event()

	def run(self):
		'''Run thread to check and add source'''
		Log.info(self._gui.labels.checking_source.replace('#', f'{self._source}'))
		for path, bad in self._source.check():
			if self._kill_event.is_set():
				Log.debug(self._gui.labels.aborted_by_user)
				self._gui.abort_source_check()
				return
			self._gui.echo(f'{path}', end='\r')
			if isinstance(bad, int):
				msg = self._gui.labels.path_too_long.replace('#1', f'{path}').replace('#2', f'{bad}').replace('#3', f'{self._gui.config.max_path_length}')
				Log.warning(msg)
				if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_path_length}', default='no'):
					self._source.max_path_len = None
				else:
					self._gui.abort_source_check()
					return
			elif isinstance(bad, str):
				msg = self._gui.labels.blacklisted.replace('#1', f'{path}').replace('#2', f'{bad}')
				Log.warning(msg)
				if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_blacklist}', default='no'):
					self._source.blacklist = None
				else:
					self._gui.abort_source_check()
					return
		if not self._gui.tolerant and not self._source.whitelist_match:
			msg = self._gui.labels.no_whitelist_match.replace('#', f'{self._source.path}')
			Log.warning(msg)
			if askyesno(title=self._gui.labels.warning, message=f'{msg}\n\n{self._gui.labels.ignore_whitelist}', default='no'):
				self._source.whitelist = None
			else:
				self._gui.abort_source_check()
				return
		self._gui.add_source(self._source)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()

class WorkThread(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Pass all attributes from GUI to work thread'''
		self._gui = gui
		super().__init__()
		self._kill_event = Event()
		self._worker = Worker(
			self._gui.sources,
			self._gui.config,
			self._gui.labels,
			self._gui.settings,
			self._gui.robocopy,
			self._gui.logger,
			trigger = self._gui.trigger,
			user_log = self._gui.log_path,
			echo = self._gui.echo,
			kill = self._kill_event
		)

	def run(self):
		'''Run thread'''
		try:
			errors = self._worker.run()
		except:
			errors = [get_exception()]
		self._gui.finished(errors)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()

class Gui(Tk):
	'''GUI look and feel'''

	@staticmethod
	def startup_error(msg):
		'''Window showing startup error'''
		showerror(title='Cirdan - Critical error on startup', message=msg)

	def __init__(self, config, labels, settings, logger, user_log=None, source=None, trigger=None, no_source_check=False):
		'''Open application window'''
		super().__init__()
		self.config = config
		self.labels = labels
		self.settings = settings
		self.log_path = user_log
		self.no_source_check = no_source_check
		self.logger = logger
		self._work_thread = None
		self._add_source_thread = None
		try:
			self.robocopy = RoboCopy()
			self._defs = Json(self.config.app_path / 'gui.json')
			self.title(f'{self.labels.title} v{self.labels.version}')
			self.rowconfigure(0, weight=1)
			self.columnconfigure(1, weight=1)
			self.rowconfigure(7, weight=1)
			self.iconphoto(True, PhotoImage(file=self.config.app_path / self._defs.appicon))
			self.protocol('WM_DELETE_WINDOW', self._quit_app)
			font = nametofont('TkTextFont').actual()
			font_family = font['family']
			font_size = font['size']
			min_size_x = font_size * self._defs.x_factor
			min_size_y = font_size * self._defs.y_factor
			self.minsize(min_size_x , min_size_y)
			self.geometry(f'{min_size_x}x{min_size_y}')
			self.resizable(True, True)
			self._pad = int(font_size * self._defs.pad_factor)
			self._source_button = Button(self, text=self.labels.source_dir, command=self._select_source)
			self._source_button.grid(row=0, column=0, sticky='nw', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			Hovertip(self._source_button, self.labels.source_tip)
			self._source_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
			self._source_text.grid(row=0, column=1, sticky='nswe', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
			if source:
				self._source_text.insert('end', f'{source}\n')
				self.sources = [source]
			else:
				self.sources = list()
			self._source_text.configure(state='disabled')
			self._source_text.bind('<Key>', lambda dummy: 'break')
			self._delete_button = Button(self, text=self.labels.delete_source, command=self._delete_source)
			self._delete_button.grid(row=1, column=1, sticky='ne', padx=self._pad)#, pady=self._pad)
			Hovertip(self._delete_button, self.labels.delete_source_tip)
			label = Label(self, text=self.labels.destination)
			label.grid(row=2, column=0, sticky='w', padx=self._pad)
			Hovertip(label, self.labels.destination_tip)
			self.destination = StringVar(value=self.settings.destination)
			if len(self.config.reachable_dsts) > 1:
				OptionMenu(
					self,
					self.destination,
					self.settings.destination if self.settings.destination else self.labels.select_destination,
					*self.config.reachable_dsts
				).grid(row=2, column=1, sticky='w', padx=self._pad)
			else:
				Label(self, text=self.settings.destination).grid(row=2, column=1, columnspan=2, sticky='w', padx=self._pad)
			label = Label(self, text=self.labels.after_copying)
			label.grid(row=3, column=0, sticky='nw', padx=self._pad, pady=(self._pad, 0))
			Hovertip(label, self.labels.after_copying_tip)
			frame = Frame(self)
			frame.grid(row=3, column=1, sticky='we', pady=(self._pad, 0))
			self.write_trigger = BooleanVar(value=self.settings.trigger)
			button = Checkbutton(frame, text=self.labels.trigger_button, variable=self.write_trigger)
			button.pack(side='left', padx=self._pad)
			Hovertip(button, self.labels.trigger_tip)

			destination = self.destination.get()

			self._triggers = self.config.destinations[destination] if destination in self.config.destinations else tuple()
			print(self._triggers)
			

			'''
			self.trigger = StringVar(
				value = (self.config.triggers['static'] if self.config.triggers['static']
					else self.config.triggers['selection'])
			)

			OptionMenu(
				frame,
				self.trigger,
				trigger if trigger else self.labels.select_trigger,
				*self._triggers
			).pack(side='left', padx=self._pad)
			'''

			frame = Frame(self)
			frame.grid(row=4, column=1, sticky='we', padx=self._pad)
			self.user = StringVar(value=self.settings.user)
			try:
				use_mail = SendMail(self.config.mail).is_reachable()
			except:
				use_mail = False
			if use_mail:
				self.send_mail = BooleanVar(value=self.settings.sendmail)
				button = Checkbutton(frame, text=self.labels.sendmail_button, variable=self.send_mail)
				button.pack(side='left')
				Hovertip(button, self.labels.sendmail_tip)
				entry = Entry(frame, textvariable=self.user)
				entry.pack(side='left', fill='x', expand=True)
				Hovertip(entry, self.labels.address_tip)
				label = Label(frame, text=f'@{self.config.domain}')
				label.pack(side='left')
				Hovertip(label, self.labels.address_tip)
			else:
				self.send_mail = BooleanVar(value=False)
			frame = Frame(self)
			frame.grid(row=5, column=1, sticky='we', padx=self._pad)
			self.write_qualicheck = BooleanVar(value=self.settings.qualicheck)
			button = Checkbutton(frame, text=self.labels.qualicheck_button, variable=self.write_qualicheck)
			button.pack(side='left', padx=(0, self._pad))
			Hovertip(button, self.labels.qualicheck_tip)
			self.write_log = BooleanVar(value=bool(self.log_path))
			button = Checkbutton(frame, text=self.labels.log_button, variable=self.write_log, comman=self._select_log)
			button.pack(side='left', padx=self._pad)
			Hovertip(button, self.labels.log_tip)
			self._exec_button = Button(self, text=self.labels.start_button, command=self._execute)
			self._exec_button.grid(row=6, column=1, sticky='e', padx=self._pad, pady=self._pad)
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
			if not self.config.app_path.resolve().drive.startswith('\\\\'):	# check for updates
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
		except:
			msg = self.logger.crash()
			showerror(title=self.labels.error, message=msg)
			self.destroy()

	def _select_source(self):
		'''Select directory to add into field'''
		if source := askdirectory(title=self.labels.select_dir, mustexist=True):
			source = Path(source).resolve()
			if source in self.sources:
				showerror(title=self.labels.error, message=self.labels.already_added.replace('#', f'{source}'))
				return
			self._check_source_thread = CheckSourceThread(source, self)
			self._check_source_thread.start()

	def add_source(self, source):
		'''Run this after adding source'''
		self._add_source_thread = None
		self._source_text.configure(state='normal')
		self._source_text.insert('end', f'{source}\n')
		self._source_text.configure(state='disabled')
		self._enable_buttons()
		self.sources.append(source)
		Log.info(self.labels.added_source.replace('#', f'{source}'))

	def abort_source_check(self):
		'''Run this after checking source and not adding it'''
		self._add_source_thread = None
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

	def _enable_buttons(self):
		'''Enable source selector and start button'''
		self._source_button.configure(state='normal')
		self._exec_button.configure(state='normal')

	def _get_settings(self):
		'''Get settings from GUI'''
		self.settings.user = self.user.get()
		self.settings.destination = self.destination.get()
		self.settings.trigger = self.write_trigger.get()
		self.settings.sendmail = self.send_mail.get()
		self.settings.qualicheck = self.write_qualicheck.get()

	def _save_settings(self):
		'''Get settings from GUI and save to JSON file'''
		self._get_settings()
		try:
			self.settings.save()
		except:
			pass

	def _execute(self):
		'''Start copy process / worker'''
		self._get_settings()
		if self.settings.sendmail and not self.settings.user:
			showerror(title=self.labels.error, message=self.labels.missing_name)
			return
		if not self.settings.destination in self.config.destinations:
			showerror(
				title = self.labels.error,
				message = self.labels.bad_destination.replace('#', f'{self.settings.destination}')
			)
			return
		self._save_settings()
		self._clear_info()
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
			self._info_label.configure(foreground=self._defs.red_fg, background=self._defs.red_bg)
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
			self._info_text.configure(foreground=self._defs.red_fg, background=self._defs.red_bg)
			self._warning_state = 'enable'
			msg = f'{self.labels.problems}:'
			if len(errors) in (1, 2, 3):
				for error in errors:
					msg += f'\n\n{error}'
			elif errors:
				msg += f'\n\n{errors[0]}\n\n{errors[1]}\n\n{self.labels.more_problems.replace("#", f"{len(errors)-2}")}'
			showerror(title=self.labels.warning, message=msg)
		else:
			self._info_text.configure(foreground=self._defs.green_fg, background=self._defs.green_bg)

	def quit_app(self):
		'''Save settings end close application window'''
		self._save_settings()
		Log.debug('Quitting application')
		self.destroy()

	def _quit_app(self):
		'''Quit app, ask if copy process is running'''
		if self._add_source_thread or self._work_thread:
			if not askyesno(title=self.labels.warning, message=self.labels.running_warning):
				return
			Log.info(self.labels.killing_running)
			try:
				self._work_thread.kill()
			except:
				pass
			try:
				self._add_source_thread.kill()
			except:
				pass
		else:
			self.quit_app()

