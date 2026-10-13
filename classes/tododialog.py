#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from traceback import format_exc as get_exception
from tkinter import Toplevel, StringVar
from tkinter.ttk import Frame, Label, Treeview, Scrollbar, Button, OptionMenu
from tkinter.messagebox import showerror
from idlelib.tooltip import Hovertip
from classes.path import Path
if TYPE_CHECKING:
	from classes.gui import Gui

class ToDoDialog(Toplevel):
	"""ToDo dialog"""

	def __init__(self, root: Gui) -> None:
		super().__init__(root)
		self._root = root
		self._labels = self._root.settings.labels
		self._destination = self._root.settings.destination
		self.title(self._labels.create_todo)
		self.minsize(self._root.min_size_x , self._root.min_size_y)
		self.geometry(f"{self._root.min_size_x}x{self._root.min_size_y}")
		self.resizable(True, True)
		frame = Frame(self)
		frame.pack(fill="x", padx=self._root._pad, pady=self._root._pad)
		Label(frame, text=self._labels.select_todo_dir).pack(side="left", padx=self._root._pad)
		frame = Frame(self)
		frame.pack(fill="both", expand=True, padx=self._root._pad, pady=(0,self._root._pad))
		self._tree = Treeview(frame, show="tree", selectmode="browse")
		for sub_dir_path in self._destination.sub_dir_paths:
			self._tree.insert("", "end", text=sub_dir_path.name, iid=f"{sub_dir_path}")
			for path in sub_dir_path.iterdir():
				if path.is_dir():
					self._tree.insert(f"{sub_dir_path}", "end", text=f"\U0001F5C2 {path.name}", iid=f"{path}")
			for path in sub_dir_path.iterdir():
				if path.is_file():
					self._tree.insert(f"{sub_dir_path}", "end", text=f"\U0001F5C5 {path.name}", iid=f"{path}")
		if len(self._destination.sub_dir_paths) == 1:
			self._tree.selection_set(f"{self._destination.sub_dir_paths[0]}")
			self._tree.focus(f"{self._destination.sub_dir_paths[0]}")
		self._tree.pack(side="left", fill="both", expand=True)
		vsb = Scrollbar(frame, orient="vertical", command=self._tree.yview)
		vsb.pack(side="right", fill="y")
		self._tree.configure(yscrollcommand=vsb.set)
		frame = Frame(self)
		frame.pack(fill="x", pady=(0, self._root._pad))
		self._todo = StringVar()
		todos = tuple[str](todo for todo in self._destination.todos.keys() if self._destination.todos[todo]["do_something"])
		if len(todos) > 1:
			element = OptionMenu(frame, self._todo)
			element.set_menu(self._labels.todo_dialog_select, *todos)
			element.configure(width=max(len(self._labels.todo_dialog_select), *(len(todo) for todo in todos)))
		else:
			element = Label(frame, text=todos[0])
			self._todo.set(todos[0])
		element.pack(side="left", padx=self._root._pad)
		Hovertip(element, self._labels.todo_tip)
		button = Button(frame, text=self._labels.cancel, command=self.destroy)
		button.pack(side="right", padx=self._root._pad)
		button = Button(frame, text=self._labels.launch, command=self._create)
		button.pack(side="right", padx=self._root._pad)

	def _create(self) -> None:
		"""Write meta and trigger files"""
		selection = self._tree.selection()
		if not selection:
			showerror(parent=self, title=self._labels.error, message=self._labels.select_destination_first)
			return
		todo = self._todo.get()
		if todo not in self._destination.todos:
			showerror(parent=self, title=self._labels.error, message=self._labels.todo_dialog_select)
			return
		selected_path = Path(selection[0])
		if not selected_path in self._destination.sub_dir_paths:
			selected_path = Path(self._tree.parent(selection[0]))
		self._root.create_todo(selected_path, todo)
