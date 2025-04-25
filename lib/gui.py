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

class GuiConfig:
	'''GUI configuration'''


	PAD = 4
	X_FACTOR = 60
	Y_FACTOR = 40
	GREEN_FG = 'black'
	GREEN_BG = 'pale green'
	RED_FG = 'black'
	RED_BG = 'coral'

	def __init__(self, user, source, target, log_dir, trigger, log):
		self.user = user
		self.source = source
		self.target = target
		self.log_dir = log_dir
		self.trigger = trigger
		self.log = log

class Gui(Tk):
	'''GUI look and feel'''


	def __init__(self, source, config, icon_path, version, log_dir=None, trigger=True):
		'''Open application window'''
		super().__init__()
		self.work_thread = None
		self.title(f'SlowCopy v{version}')
		self.rowconfigure(1, weight=1)
		self.columnconfigure(1, weight=1)
		self.rowconfigure(3, weight=1)
		self.iconphoto(True, PhotoImage(file=icon_path))
		self.protocol('WM_DELETE_WINDOW', self._quit_app)
		font = nametofont('TkTextFont').actual()
		self.font_family = font['family']
		self.font_size = font['size']
		self.min_size_x = self.font_size * self.X_FACTOR
		self.min_size_y = self.font_size * self.Y_FACTOR
		self.minsize(self.min_size_x , self.min_size_y)
		self.geometry(f'{self.min_size_x}x{self.min_size_y}')
		self.resizable(True, True)
		self.padding = int(self.font_size / self.PAD)
		frame = Frame(self)
		frame.grid(row=0, column=0, columnspan=2, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		self.user = StringVar(value=config.user)
		Entry(frame, textvariable=self.user).pack(padx=self.padding, pady=self.padding)
		
		

		#OptionMenu(container, variable, default=None, *values, **kwargs)


		Label(frame, text=f'Distribution {config.user}').pack(padx=self.padding, pady=self.padding)
		frame = Frame(self)
		frame.grid(row=1, column=0,	sticky='n')
		self.source_button = Button(frame, text='Quellverzeichnis', command=self._select_dir)
		self.source_button.pack(padx=self.padding, pady=self.padding, fill='x', expand=True)
		Hovertip(self.source_button, 'Füge das zu kopierende Verzeichnis hinzu (POLIKS-Vorgangsnummer).')
		Label(frame, text='Optionen:').pack(
			padx=self.padding, pady=(self.padding*8, self.padding), fill='x', expand=True)
		self.generate_trigger = BooleanVar(value=True)
		self.trigger_button = Checkbutton(frame, text='Weiterverarbeitung', variable=self.generate_trigger)
		self.trigger_button.pack(padx=self.padding, pady=self.padding, fill='x', expand=True)
		Hovertip(self.trigger_button, '''Angehakt wird die Weiterverarbeitung ausgelöst bzw.
eine "fertig.txt"-Datei im Importverzeichnis erstellt.
Wird der Haken entfernt, könne weitere Daten unter der
betreffenden POLIKS-Nummer hochgeladen werden.''')
		self.write_log = BooleanVar(value=False)
		self.log_button = Checkbutton(frame, text='Schreibe Log', variable=self.write_log)
		self.log_button.pack(padx=self.padding, pady=self.padding, fill='x', expand=True)
		Hovertip(self.log_button, '''Angehakt wird eine Protokolldateien erzeugt.
Hierfür wird nach abgeschlossenem
Kopiervorgang ein Dialog geöffnet.''')
		self.source_text = ScrolledText(self, font=(self.font_family, self.font_size),
			padx = self.padding, pady = self.padding)
		self.source_text.grid(row=1, column=1, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		frame = Frame(self)
		frame.grid(row=2, column=1, sticky='news', padx=self.padding, pady=self.padding)
		Label(frame, text='Kopiere ins MSD-Importverzeichnis').pack(padx=self.padding, pady=self.padding, side='left')
		self.exec_button = Button(frame, text='Start', command=self._execute)
		self.exec_button.pack(padx=self.padding, pady=self.padding, side='right')
		Hovertip(self.exec_button, 'Starte den Kopiervorgang')
		self.info_text = ScrolledText(self, font=(self.font_family, self.font_size),
			padx = self.padding, pady = self.padding)
		self.info_text.grid(row=3, column=0, columnspan=2, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		self.info_text.bind('<Key>', lambda dummy: 'break')
		self.info_text.configure(state='disabled')
		self.info_fg = self.info_text.cget('foreground')
		self.info_bg = self.info_text.cget('background')
		self.info_newline = True
		frame = Frame(self)
		frame.grid(row=4, column=1, sticky='news', padx=self.padding, pady=self.padding)
		self.info_label = Label(frame)
		self.info_label.pack(padx=self.padding, pady=self.padding, side='left')
		self.label_fg = self.info_label.cget('foreground')
		self.label_bg = self.info_label.cget('background')
		self.quit_button = Button(frame, text='Verlassen', command=self._quit_app)
		self.quit_button.pack(padx=self.padding, pady=self.padding, side='right')

		return


		update = Update(config.update)
		if update.version and askyesno(
			title = f'Eine neuere Version steht bereit ({update.version}!',
			message = 'Neu Version herunterladen und diese Anwendung verlassen?'
		):
			if directory := askdirectory(title='Wähle das Zielverzeichnis für die neue Slowcopy-Version', mustexist=True):
				try:
					copy = RoboCopy().copy_file(update.get_path(config.user), Path(directory))
					if copy.returncode != 1:
						raise OSError(f'Robocopy gab den Returncode {copy.returncode} zurück.')
				except Exception as ex:
					showerror(
						title = 'Fehler',
						message= f'Die neue Version von SlowCopy konnte nicht nach {directory} kopiert werden:\n{ex}'
					)
				self.destroy()
		else:
			self._init_warning()
			self.check_paths = True
			self._add_dir(dir_path)

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
		self.source_text.insert('end', f'{dir_path}\n')

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
			self.info_text.configure(foreground=self.GREEN_FG, background=self.GREEN_BG)
		if self.write_log.get() and log:
			file_name = asksaveasfilename(title='Protokolldatei', defaultextension='.txt')
			if file_name:
				Path(file_name).write_text(log)
		self.source_text.configure(state='normal')
		self.source_text.delete('1.0', 'end')
		self.source_button.configure(state='normal')
		self.exec_button.configure(state='normal')
		self.quit_button.configure(state='normal')
		self.worker = None

	def _quit_app(self):
		'''Quit app, ask when copy processs is running'''
		if self.work_thread and not askyesno(
			title='Kopiervorgang läuft!',
			message='Wirklich die Anwendung verlassen und den Kopiervorgang abbrechen?'
		):
			return
		self.destroy()
