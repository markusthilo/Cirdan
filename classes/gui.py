#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from threading import Thread, Event
from pathlib import Path
from tkinter import Tk, PhotoImage, StringVar, BooleanVar
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror
from tkinter.filedialog import askdirectory, asksaveasfilename
from idlelib.tooltip import Hovertip
from classes.worker import Worker
from classes.json import Json
from classes.update import Update
from classes.pathhandler import PathHandler

class WorkThread(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Pass all attributes from GUI to work thread'''
		self._gui = gui
		super().__init__()
		self._kill_event = Event()
		self._worker = Worker(gui.app_path, gui.config, gui.labels, gui.settings,
			local_log = gui.log_path,
			echo = self._gui.echo,
			kill = self._kill_event
		)

	def run(self):
		'''Run thread'''
		error = False
		for src_path in self._gui.source_paths:
			try:
				self._worker.copy_dir(src_path)
			except Exception as ex:
				logging.error(f'{type(ex)}: {ex}')
				self._gui.echo(f'{self._gui.labels.error} ({type(ex).__name__}): {ex}')
				error = True
		del self._worker
		self._gui.finished(error)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()

class Gui(Tk):
	'''GUI look and feel'''

	def __init__(self, app_path, config, labels, settings, log=None, source=None):
		'''Open application window'''
		super().__init__()
		self.app_path = app_path
		self.config = config
		self.labels = labels
		self.settings = settings
		self._defs = Json(app_path / 'gui.json')
		self.log_path = log
		self._work_thread = None
		self.title(f'SlowCopy v{self.labels.version}')
		self.rowconfigure(0, weight=1)
		self.columnconfigure(1, weight=1)
		self.rowconfigure(5, weight=1)
		self.iconphoto(True, PhotoImage(file=self.app_path / self._defs.appicon))
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
		self._source_button = Button(self, text=self.labels.source_dir, command=self._select_dir)
		self._source_button.grid(row=0, column=0, sticky='nw', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
		Hovertip(self._source_button, self.labels.source_tip)
		self._source_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
		self._source_text.grid(row=0, column=1, sticky='nsew', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
		if source:
			self._source_text.insert('end', f'{source}\n')
		label = Label(self, text=self.labels.user_label)
		label.grid(row=1, column=0, sticky='w', padx=self._pad, pady=self._pad)
		Hovertip(label, self.labels.user_tip)
		frame = Frame(self)
		frame.grid(row=1, column=1, sticky='w', padx=self._pad)
		self.user = StringVar(value=self.settings.user)
		Entry(frame, textvariable=self.user, width=self._defs.user_width).pack(side='left', anchor='w')
		Label(frame, text=f'@{self.config.domain}').pack(side='right', anchor='w')
		label = Label(self, text=self.labels.destination)
		label.grid(row=2, column=0, sticky='w', padx=self._pad)
		Hovertip(label, self.labels.destination_tip)
		self._path_handler = PathHandler(config, labels)
		self.destinations = tuple(
			dst for dst in self.config.destinations
			if self._path_handler.is_accessable_dir(self.config.target_path.joinpath(self.config.destinations[dst]))
		)
		self.destination = StringVar()
		if len(self.destinations) == 1:
			self.settings.destination = self.destinations[0]
			self.destination.set(self.destinations[0])
			Label(self, text=self.destinations[0]).grid(row=2, column=1, sticky='w', padx=self._pad)
		elif len(self.destinations) > 1:
			if not self.settings.destination:
				self.settings.destination = self.destinations[0]
			OptionMenu(self, self.destination, self.settings.destination, *self.destinations
				).grid(row=2, column=1, sticky='w', padx=self._pad)
		Label(self, text=self.labels.options).grid(row=3, column=0, sticky='nw', padx=self._pad, pady=(self._pad, 0))
		frame = Frame(self)
		frame.grid(row=3, column=1, sticky='w', pady=(self._pad, 0))
		self.write_trigger = BooleanVar(value=self.settings.trigger)
		button = Checkbutton(frame, text=self.labels.trigger_button, variable=self.write_trigger)
		button.grid(row=0, column=0, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.trigger_tip)
		self.send_mail = BooleanVar(value=self.settings.sendmail)
		button = Checkbutton(frame, text=self.labels.sendmail_button, variable=self.send_mail)
		button.grid(row=0, column=1, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.sendmail_tip)
		self.write_qualicheck = BooleanVar(value=self.settings.qualicheck)
		button = Checkbutton(frame, text=self.labels.qualicheck_button, variable=self.write_qualicheck)
		button.grid(row=1, column=0, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.qualicheck_tip)
		self.write_log = BooleanVar(value=bool(self.log_path))
		button = Checkbutton(frame, text=self.labels.log_button, variable=self.write_log, comman=self._select_log)
		button.grid(row=1, column=1, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.log_tip)
		self._exec_button = Button(self, text=self.labels.start_button, command=self._execute)
		self._exec_button.grid(row=4, column=1, sticky='e', padx=self._pad, pady=self._pad)
		Hovertip(self._exec_button, self.labels.start_tip)
		self._info_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
		self._info_text.grid(row=5, column=0, columnspan=2, sticky='nsew',
			ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
		self._info_text.bind('<Key>', lambda dummy: 'break')
		self._info_text.configure(state='disabled')
		self._info_fg = self._info_text.cget('foreground')
		self._info_bg = self._info_text.cget('background')
		self._info_newline = True
		self._info_label = Label(self)
		self._info_label.grid(row=6, column=0, sticky='w', padx=self._pad, pady=self._pad)
		self._label_fg = self._info_label.cget('foreground')
		self._label_bg = self._info_label.cget('background')
		self._quit_button = Button(self, text=self.labels.quit, command=self._quit_app)
		self._quit_button.grid(row=6, column=1, sticky='e', padx=self._pad, pady=self._pad)
		update = Update(self.labels.version, self.config.update_path)
		if update.new_version and askyesno(
			title = self.labels.update_title.replace('#', update.new_version),
			message = self.labels.update_message
		):
			try:
				update.download(self.app_path)
				self.destroy()
				return
			except Exception as ex:
				showerror(
					title = self.labels.error,
					message= f'{self.labels.update_error}:\n{type(ex).__name__}: {ex}'
				)
		if not self.destinations:
			if self.settings.destination:
				showerror(title=self.labels.error, message=self.labels.bad_destination.replace('#', self.settings.destination))
			else:
				showerror(title=self.labels.error, message=self.labels.no_destination)
			self.destroy()
			return
		if not self._path_handler.is_accessable_dir(self.config.log_path):
			showerror(title=self.labels.error, message=self.labels.bad_log_dir.replace('#', f'{self.config.log_path}'))
			self.destroy()
			return
		if not self._path_handler.is_accessable_dir(self.config.mail_path):
			showerror(title=self.labels.error, message=self.labels.bad_mail_dir.replace('#', f'{self.config.mail_path}'))
			self.destroy()
			return
		self._ignore_warning = False
		self._init_warning()

	def _get_source_paths(self):
		'''Read directory paths from text field'''
		text = self._source_text.get('1.0', 'end').strip()
		good_paths = set()
		bad_paths = set()
		if text:
			for line in text.split('\n'):
				stripped = line.strip()
				try:
					good_paths.add(Path(stripped).resolve())
				except:
					bad_paths.add(stripped)
		return good_paths, bad_paths

	def _add_dir(self, dir_path):
		'''Add directory into field'''
		if not dir_path:
			return
		dir_path = dir_path.resolve()
		self.echo(self.labels.checking_source.replace('#', f'{dir_path}'), end='\r')
		try:
			self._path_handler.check_source_path(dir_path)
		except Exception as ex:
			self.echo('', end='\r')
			showerror(title=self.labels.error, message=f'{type(ex).__name__}: {ex}')
			return
		self.echo('', end='\r')
		old_paths, bad_paths = self._get_source_paths()
		if old_paths and path in old_paths:
			return
		self._source_text.insert('end', f'{dir_path}\n')

	def _select_dir(self):
		'''Select directory to add into field'''
		directory = askdirectory(title=self.labels.select_dir, mustexist=True)
		if directory:
			self._add_dir(Path(directory))

	def _select_log(self):
		'''Select directory '''
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
		self.source_paths, bad_paths = self._get_source_paths()
		if bad_paths:
			showerror(title=self.labels.error, message=f'{self.labels.bad_sources}: {"\n ".join(bad_paths)}')
		if not self.source_paths:
			showerror(title=self.labels.error, message=self.labels.missing_source_dir)
			return
		self._get_settings()
		if not self.settings.user:
			showerror(title=self.labels.error, message=self.labels.missing_name)
			return
		if not self.settings.destination in self.config.destinations:
			showerror(
				title = self.labels.error,
				message = self.labels.bad_destination.replace('#', f'{self.settings.destination}')
			)
			return
		self._save_settings()
		self._source_button.configure(state='disabled')
		self._source_text.configure(state='disabled')
		self._exec_button.configure(state='disabled')
		self._clear_info()
		self._work_thread = WorkThread(self).start()

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

	def finished(self, error):
		'''Run this when worker has finished'''
		if error:
			self._info_text.configure(foreground=self._defs.red_fg, background=self._defs.red_bg)
			self._warning_state = 'enable'
			msg = self.labels.problems
			if error != True:
				msg += f': {error}'
			showerror(title=self.labels.warning, message=msg)
		else:
			self._info_text.configure(foreground=self._defs.green_fg, background=self._defs.green_bg)
		self._source_text.configure(state='normal')
		self._source_text.delete('1.0', 'end')
		self.write_log.set(False)
		self.log_path = None
		self._source_button.configure(state='normal')
		self._exec_button.configure(state='normal')
		self._quit_button.configure(state='normal')
		self._work_thread = None

	def _quit_app(self):
		'''Quit app, ask when copy processs is running'''
		if self._work_thread:
			if not askyesno(title=self.labels.warning, message=self.labels.running_warning):
				return
			self._work_thread.kill()
		self._save_settings()
		self.destroy()
