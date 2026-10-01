#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from traceback import format_exc as get_exception
from tkinter import Toplevel, StringVar
from tkinter.ttk import Frame, Label, Treeview, Scrollbar, Button, OptionMenu
from tkinter.messagebox import showerror
from idlelib.tooltip import Hovertip
from classes.path import Path
from classes.todo import ToDo

class ToDoDialog(Toplevel):
	'''ToDo dialog'''

	def __init__(self, root, destinaton):
		'''Dialog settings'''
		super().__init__(root)
		self._root = root
		self._destination = destinaton
		self.title(self._root.labels.create_todo)
		self.minsize(self._root.min_size_x , self._root.min_size_y)
		self.geometry(f'{self._root.min_size_x}x{self._root.min_size_y}')
		self.resizable(True, True)
		frame = Frame(self)
		frame.pack(fill='x', padx=self._root._pad, pady=(0,self._root._pad))
		Label(frame, text=self._root.labels.select_todo_dir).pack(side='left', padx=self._root._pad)
		frame = Frame(self)
		frame.pack(fill='both', expand=True, padx=self._root._pad, pady=(0,self._root._pad))
		self._tree = Treeview(frame, show='tree', selectmode='browse')
		for sub_dir_path in self._destination.sub_dir_paths:
			self._tree.insert('', 'end', text=sub_dir_path.name, iid=f'{sub_dir_path}')
			for path in sub_dir_path.iterdir():
				if path.is_dir():
					self._tree.insert(f'{sub_dir_path}', 'end', text=f'\U0001F5C2 {path.name}')
			for path in sub_dir_path.iterdir():
				if path.is_file():
					self._tree.insert(f'{sub_dir_path}', 'end', text=f'\U0001F5C5 {path.name}')
		self._tree.pack(side='left', fill='both', expand=True)
		vsb = Scrollbar(frame, orient='vertical', command=self._tree.yview)
		vsb.pack(side='right', fill='y')
		self._tree.configure(yscrollcommand=vsb.set)
		frame = Frame(self)
		frame.pack(fill='x', pady=self._root._pad)
		self._todo = StringVar()
		menu = OptionMenu(frame, self._todo)
		self._todo_dict = self._root.config.todo[self._root.config.destinations[self._root.destination.get()]['todo']]
		if len(self._todo_dict) > 1:
			menu.set_menu(self._root.labels.todo_dialog_select, *self._todo_dict.keys())
		else:
			self._todo.set(next(iter(self._todo_dict.keys())))
		menu.pack(side='left', padx=self._root._pad)
		Hovertip(menu, self._root.labels.todo_tip)
		button = Button(frame, text=self._root.labels.cancel, command=self.destroy)
		button.pack(side='right', padx=self._root._pad)
		button = Button(frame, text=self._root.labels.launch, command=self._create)
		button.pack(side='right', padx=self._root._pad)

	def _create(self):
		selection = self._tree.selection()
		if not selection:
			showerror(parent=self, title=self._root.labels.error, message=self._root.labels.select_destination_first)
			return
		todo = ToDo(self._todo.get(), self._root.settings, self._root.config)
		if not todo.trigger_name:
			showerror(parent=self, title=self._root.labels.error, message=self._root.labels.missing_todo_msg)
			return
		selected_path = Path(selection[0])
		if not selected_path in self._destination.sub_dir_paths:
			selected_path = Path(self._tree.parent(selection[0]))
		for relative in self._destination.count_paths(selected_path):
			self._root.echo(f'{self._root.labels.checking} {relative}')
		try:
			todo.delete_trigger(selected_path)
			todo.write_meta(selected_path, self._destination.counted_paths)
			todo.write_trigger(selected_path, self._root.logger.id)
		except:
			showerror(parent=self, title=self._root.labels.error, message=get_exception())
			return
		self._root.echo(self._root.labels.todo_created.replace('#1', f'{todo}').replace('#2', selected_path.name))
		self.destroy()
