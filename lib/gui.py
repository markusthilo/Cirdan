#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from tkinter import Tk, PhotoImage, StringVar, BooleanVar
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Entry, Button, Checkbutton, OptionMenu
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror
from tkinter.filedialog import askdirectory, asksaveasfilename
from idlelib.tooltip import Hovertip
from lib.config import Config
from lib.update import Update

class Gui(Tk):
	'''GUI look and feel'''

	def __init__(self, directory, config, app_path, version, log_dir=None, trigger=True):
		'''Open application window'''
		super().__init__()
		self._work_thread = None
		self._config = config
		self._defs = Config(app_path / 'gui.json')
		self._labels = Config(app_path / 'labels.json')
		self.title(f'SlowCopy v{version}')
		self.rowconfigure(0, weight=1)
		self.columnconfigure(1, weight=1)
		self.rowconfigure(5, weight=1)
		self.iconphoto(True, PhotoImage(file=app_path / self._defs.appicon))
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
		self._source_button = Button(self, text=self._labels.source_dir, command=self._select_dir)
		self._source_button.grid(row=0, column=0, sticky='nw', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
		Hovertip(self._source_button, self._labels.source_tip)
		self._source_text = ScrolledText(self, font=(font_family, font_size), padx=self._pad, pady=self._pad)
		self._source_text.grid(row=0, column=1, sticky='nsew', ipadx=self._pad, ipady=self._pad, padx=self._pad, pady=self._pad)
		label = Label(self, text=self._labels.user_label)
		label.grid(row=1, column=0, sticky='w', padx=self._pad, pady=self._pad)
		Hovertip(label, self._labels.user_tip)
		frame = Frame(self)
		frame.grid(row=1, column=1, sticky='w', padx=self._pad)
		self._user = StringVar(value=self._config.user)
		Entry(frame, textvariable=self._user, width=self._defs.user_width).pack(side='left', anchor='w')
		Label(frame, text=f'@{self._config.domain}').pack(side='right', anchor='w')
		label = Label(self, text=self._labels.group_label)
		label.grid(row=2, column=0, sticky='w', padx=self._pad)
		Hovertip(label, self._labels.group_tip)
		self._group = StringVar()
		OptionMenu(self, self._group, self._config.group, *self._config.groups).grid(row=2, column=1, sticky='w', padx=self._pad)
		Label(self, text=self._labels.options).grid(row=3, column=0, sticky='w', padx=self._pad, pady=(self._pad, 0))
		frame = Frame(self)
		frame.grid(row=3, column=1, sticky='w', pady=(self._pad, 0))
		self.generate_trigger = BooleanVar(value=True)
		button = Checkbutton(frame, text=self._labels.trigger_button, variable=self.generate_trigger)
		button.pack(anchor='w', side='left', padx=self._pad)
		Hovertip(button, self._labels.trigger_tip)
		self.write_log = BooleanVar(value=False)
		button = Checkbutton(frame, text=self._labels.log_button, variable=self.write_log)
		button.pack(anchor='w', side='left', padx=self._pad)
		Hovertip(button, self._labels.log_tip)
		self.exec_button = Button(self, text=self._labels.start_button, command=self._execute, state='disabled')
		self.exec_button.grid(row=4, column=1, sticky='e', padx=self._pad, pady=self._pad)
		Hovertip(self.exec_button, self._labels.start_tip)
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
		self._quit_button = Button(self, text=self._labels.quit, command=self._quit_app)
		self._quit_button.grid(row=6, column=1, sticky='e', padx=self._pad, pady=self._pad)
		update = Update(version, Path(self._config.update))
		if update.version and askyesno(
			title = self._labels.update_title.replace('#', update.version),
			message = self._labels.update_message
		):
			if directory := askdirectory(title=self._labels.update_dir, mustexist=True):
				try:
					update.install(Path(directory))
				except Exception as ex:
					showerror(
						title = self._labels.error,
						message= f'{self._labels.update_error}:\n{ex}'
					)
				self.destroy()
		else:
			self._init_warning()
			self._check_paths = True
			if directory:
				self._add_dir(directory)
				self._exec_button(state='normal')

	def _add_dir(self, directory):
		'''Add directorself.appicon = PhotoImage(file=self.parent_path/'appicon.png')
		self.iconphoto(True, self.appicon)y into field'''
		if not directory:
			return
		dir_path = Path(directory).absolute()
		old_paths = self._get_source_paths()
		if old_paths and dir_path in old_paths:
			return
		error = Copy.bad_source(dir_path)
		if error:
			showerror(title='Fehler', message=error)
			return
		for path, msg in Copy.blacklisted_files(dir_path):
			if not path:
				break
			if askyesno(
				title = f'Datei löschen?',
				message = f'{msg}\n\nDatei löschen oder Abbrechen?'
			):
				try:
					path.unlink()
				except Exception as ex:
					showerror(title='Fehler', message=f'Konnte Datei {path} nicht löschen:\n{ex}')
					return
		for path, msg in Copy.blacklisted_paths(dir_path):
			if not path:
				break
			if askyesno(
				title = f'Verzeichnis löschen?',
				message = f'{msg}\n\nVerzeichnis löschen?'
			):
				try:
					rmtree(path)
				except Exception as ex:
					showerror(title='Fehler', message=f'Konnte Verzeichnis {path} nicht löschen:\n{ex}')
					return
			else:
				if askyesno(
					title = f'Fortfahren?',
					message = f'{msg}\n\nTrotzdem fortfahren und Verzeichnis hinzufügen?'
				):
					self.check_paths = False
				else:
					return
		self._source_text.insert('end', f'{dir_path}\n')
		self._exec_button(state='normal')

	def _select_dir(self):
		'''Select directory to add into field'''
		directory = askdirectory(title='Wähle das Quellverzeichnis aus', mustexist=True)
		if directory:
			self._add_dir(directory)

	def echo(self, *arg, end=None):
		'''Write message to info field (ScrolledText)'''
		msg = ' '.join(arg)
		self.info_text.configure(state='normal')
		if not self.info_newline:
			self.info_text.delete('end-2l', 'end-1l')
		self.info_text.insert('end', f'{msg}\n')
		self.info_text.configure(state='disabled')
		if self.info_newline:
			self.info_text.yview('end')
		self.info_newline = end != '\r'

	def _clear_info(self):
		'''Clear info text'''
		self.info_text.configure(state='normal')
		self.info_text.delete('1.0', 'end')
		self.info_text.configure(state='disabled')
		self.info_text.configure(foreground=self.info_fg, background=self.info_bg)
		self._warning_state = 'stop'

	def _get_source_paths(self):
		'''Start copy process / worker'''
		text = self.source_text.get('1.0', 'end').strip()
		if text:
			return [Path(source_dir.strip()).absolute() for source_dir in text.split('\n')]
		
	def _execute(self):
		'''Start copy process / worker'''
		self.source_paths = self._get_source_paths()
		if not self.source_paths:
			return
		self.source_button.configure(state='disabled')
		self.source_text.configure(state='disabled')
		self.exec_button.configure(state='disabled')
		self._clear_info()
		self.work_thread = WorkThread(self)
		self.work_thread.start()

	def _init_warning(self):
		'''Init warning functionality'''
		self._warning_state = 'disabled'
		self._warning()

	def _warning(self):
		'''Show flashing warning'''
		if self._warning_state == 'enable':
			self.info_label.configure(text='ACHTUNG!')
			self._warning_state = '1'
		if self._warning_state == '1':
			self.info_label.configure(foreground=self.RED_FG, background=self.RED_BG)
			self._warning_state = '2'
		elif self._warning_state == '2':
			self.info_label.configure(foreground=self.label_fg, background=self.label_bg)
			self._warning_state = '1'
		elif self._warning_state != 'disabled':
			self.info_label.configure(text= '', foreground=self.label_fg, background=self.label_bg)
			self._warning_state = 'disabled'
		self.after(500, self._warning)

	def finished(self, errors, log):
		'''Run this when Worker has finished'''
		if errors:
			self.info_text.configure(foreground=self.RED_FG, background=self.RED_BG)
			self._warning_state = 'enable'
			showerror(
				title = 'Achtung',
				message= 'Es traten Fehler auf'
			)
		else:
			self._info_text.configure(foreground=self.GREEN_FG, background=self.GREEN_BG)
		if self.write_log.get() and log:
			file_name = asksaveasfilename(title='Protokolldatei', defaultextension='.txt')
			if file_name:
				Path(file_name).write_text(log)
		self._source_text.configure(state='normal')
		self._source_text.delete('1.0', 'end')
		self._source_button.configure(state='normal')
		self._exec_button.configure(state='normal')
		self._quit_button.configure(state='normal')
		self._worker = None

	def _quit_app(self):
		'''Quit app, ask when copy processs is running'''
		if not self._work_thread or askyesno(title=self._labels.warning, message=self._labels.running_warning):
			self._config.user = self._user.get()
			self._config.group = self._group.get()
			try:
				self._config.save()
			except:
				pass
			self.destroy()
