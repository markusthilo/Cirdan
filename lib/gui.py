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
from lib.worker import Worker
from lib.update import Update
from lib.checker import Checker

class WorkThread(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Pass all attributes from GUI to work thread'''
		self._gui = gui
		super().__init__()
		self._kill_event = Event()
		self._worker = Worker(gui.app_path, gui.config, gui.labels,
			done = gui.send_done.get(),
			finished = gui.send_finished.get(),
			log = gui.log_path if self._gui.write_log.get() else None,
			trigger = gui.write_trigger.get(),
			echo = gui.echo,
			kill = self._kill_event
		)		

	def run(self):
		'''Run thread'''
		error = True
		for src_path in self._gui.source_paths:
			try:
				self._worker.copy_dir(src_path)
				error = False
			except Exception as ex:
				logging.error(f'{type(ex)}: {ex}')
				self._gui.echo(f'{type(ex)}: {ex}')
		try:
			logging.shutdown()
		except:
			pass
		self._gui.finished(error)

	def kill(self):
		'''Kill thread'''
		self._kill_event.set()

class Gui(Tk):
	'''GUI look and feel'''

	def __init__(self, directory, app_path, config, labels, gui_defs, version,
			  done=False, finished=True, log=None, trigger=True):
		'''Open application window'''
		super().__init__()
		self.app_path = app_path
		self.config = config
		self.labels = labels
		self._defs = gui_defs
		self.log_path = log
		self._work_thread = None
		self.title(f'SlowCopy v{version}')
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
		label = Label(self, text=self.labels.user_label)
		label.grid(row=1, column=0, sticky='w', padx=self._pad, pady=self._pad)
		Hovertip(label, self.labels.user_tip)
		frame = Frame(self)
		frame.grid(row=1, column=1, sticky='w', padx=self._pad)
		self.user = StringVar(value=self.config.user)
		Entry(frame, textvariable=self.user, width=self._defs.user_width).pack(side='left', anchor='w')
		Label(frame, text=f'@{self.config.domain}').pack(side='right', anchor='w')
		label = Label(self, text=self.labels.destination)
		label.grid(row=2, column=0, sticky='w', padx=self._pad)
		Hovertip(label, self.labels.destination_tip)
		self.destination = StringVar()
		OptionMenu(self, self.destination, self.config.destination, *self.config.destinations
			).grid(row=2, column=1, sticky='w', padx=self._pad)
		Label(self, text=self.labels.options).grid(row=3, column=0, sticky='nw', padx=self._pad, pady=(self._pad, 0))
		frame = Frame(self)
		frame.grid(row=3, column=1, sticky='w', pady=(self._pad, 0))
		self.write_trigger = BooleanVar(value=trigger)
		button = Checkbutton(frame, text=self.labels.trigger_button, variable=self.write_trigger)
		button.grid(row=0, column=0, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.trigger_tip)
		self.send_finished = BooleanVar(value=finished)
		button = Checkbutton(frame, text=self.labels.finished_button, variable=self.send_finished)
		button.grid(row=0, column=1, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.finished_tip)
		self.send_done = BooleanVar(value=done)
		button = Checkbutton(frame, text=self.labels.done_button, variable=self.send_done)
		button.grid(row=1, column=0, sticky='w', padx=self._pad)
		Hovertip(button, self.labels.done_tip)
		self.write_log = BooleanVar(value=bool(log))
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
		update = Update(version, Path(self.config.update))
		if update.new_version and askyesno(
			title = self.labels.update_title.replace('#', update.new_version),
			message = self.labels.update_message
		):
			if install_dir := askdirectory(title=self.labels.update_dir, mustexist=False):
				install_path = Path(install_dir)
				if any(install_path.iterdir()) and not install_path.samefile(app_path):
					showerror(
						title = self.labels.error,
						message= f'{self.labels.update_error}:\n{self.labels.dir_not_empty}'
					)
				else:
					try:
						update.download(install_path, app_path)
						self.destroy()
					except Exception as ex:
						showerror(
							title = self.labels.error,
							message= f'{self.labels.update_error}:\n{type(ex)}: {ex}'
						)
		self._check = Checker(config)
		try:
			self._check.target()
		except Exception as ex:
			try:
				msg = self.labels.__dict__[type(ex).__name__.lower()].replace('#', str(ex))
			except:
				msg = f'{type(ex).__name__}: {ex}'
			showerror(title=self.labels.error, message=msg)
			return
		self._ignore_warning = False
		self._init_warning()
		if directory:
			self._add_dir(directory)

	def _get_source_paths(self):
		'''Read directory paths from text field'''
		text = self._source_text.get('1.0', 'end').strip()
		if text:
			return [Path(source_dir.strip()) for source_dir in text.split('\n')]

	def _add_dir(self, dir_path):
		'''Add directory into field'''
		if not dir_path:
			return
		dir_path = dir_path.absolute()
		old_paths = self._get_source_paths()
		if old_paths and dir_path in old_paths:
			return
		try:
			self._check.source(dir_path)
		except Exception as ex:
			try:
				msg = self.labels.__dict__[type(ex).__name__.lower()].replace('#', str(ex))
			except:
				msg = f'{type(ex).__name__}: {ex}'
			if isinstance(ex, RuntimeWarning):
				if askyesno(title=self.labels.warning, message=f'{msg}\n\n{self.labels.ignore}'):
					self._ignore_warning = True
				else:
					return
			else:
				showerror(title=self.labels.error, message=msg)
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
					(self.labels.logfile, f'*.{defaultextension}'),
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
			print(filename)

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

	def _execute(self):
		'''Start copy process / worker'''
		self.source_paths = self._get_source_paths()
		if not self.source_paths:
			return
		for source_path in self.source_paths:
			try:
				self._check.destination(source_path)
			except Exception as ex:
				if isinstance(ex, PermissionError):
					showerror(
						title = self.labels.error,
						message = self.labels.permissionerror.replace('#', f'{ex}')
					)
				return
		self._source_button.configure(state='disabled')
		self._source_text.configure(state='disabled')
		self._exec_button.configure(state='disabled')
		self._clear_info()
		try:
			self._work_thread = WorkThread(self)
		except:
			self.finished(True)
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

	def finished(self, error):
		'''Run this when worker has finished'''
		if error:
			self._info_text.configure(foreground=self._defs.red_fg, background=self._defs.red_bg)
			self._warning_state = 'enable'
			showerror(title=self.labels.warning, message=self.labels.problems)
		else:
			self._info_text.configure(foreground=self._defs.green_fg, background=self._defs.green_bg)
		self._source_text.configure(state='normal')
		self._source_text.delete('1.0', 'end')
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
		self.config.user = self.user.get()
		self.config.destination = self.destination.get()
		try:
			self.config.save()
		except:
			pass
		self.destroy()
