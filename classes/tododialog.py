#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING
from tkinter import Toplevel, StringVar
from tkinter.ttk import Frame, Label, Treeview, Scrollbar, Button, OptionMenu
from tkinter.messagebox import showerror
from idlelib.tooltip import Hovertip
from classes.path import Path
from classes.messagedialog import prepare_message_parent
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
		self.transient(root)
		self.grab_set()
		self.protocol("WM_DELETE_WINDOW", self.destroy)
		self.minsize(self._root.min_size_x, self._root.min_size_y)
		self.geometry(f"{self._root.min_size_x}x{self._root.min_size_y}")
		self.resizable(True, True)
		pad = self._root._pad

		frame = Frame(self)
		frame.pack(fill="x", padx=pad, pady=pad)
		Label(frame, text=self._labels.select_todo_dir).pack(side="left", padx=pad)

		frame = Frame(self)
		frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
		self._tree = Treeview(frame, show="tree", selectmode="browse")
		for sub_dir_path in self._destination.sub_dir_paths:
			parent_iid = f"{sub_dir_path}"
			self._tree.insert("", "end", text=sub_dir_path.name, iid=parent_iid)
			try:
				entries = list(sub_dir_path.iterdir())
			except OSError:
				continue
			for path in entries:
				if path.is_dir():
					self._tree.insert(parent_iid, "end", text=f"\U0001F5C2 {path.name}", iid=f"{path}")
			for path in entries:
				if path.is_file():
					self._tree.insert(parent_iid, "end", text=f"\U0001F5C5 {path.name}", iid=f"{path}")
		if len(self._destination.sub_dir_paths) == 1:
			only = f"{self._destination.sub_dir_paths[0]}"
			self._tree.selection_set(only)
			self._tree.focus(only)
		self._tree.pack(side="left", fill="both", expand=True)
		vsb = Scrollbar(frame, orient="vertical", command=self._tree.yview)
		vsb.pack(side="right", fill="y")
		self._tree.configure(yscrollcommand=vsb.set)

		frame = Frame(self)
		frame.pack(fill="x", pady=(0, pad))
		self._todo = StringVar()
		todos = tuple(
			todo for todo, cfg in self._destination.todos.items() if cfg.get("do_something")
		)
		if not todos:
			self._prepare_dialog()
			showerror(parent=self, title=self._labels.error, message=self._labels.todo_dialog_select)
			self.after_idle(self.destroy)
			return
		if len(todos) > 1:
			element = OptionMenu(frame, self._todo)
			element.set_menu(self._labels.todo_dialog_select, *todos)
			element.configure(
				width=max(len(self._labels.todo_dialog_select), *(len(todo) for todo in todos))
			)
		else:
			element = Label(frame, text=todos[0])
			self._todo.set(todos[0])
		element.pack(side="left", padx=pad)
		tip = getattr(self._labels, "todo_dialog_tip", None) or self._labels.todo_tip
		Hovertip(element, tip)
		Button(frame, text=self._labels.cancel, command=self.destroy).pack(side="right", padx=pad)
		Button(frame, text=self._labels.launch, command=self._create).pack(side="right", padx=pad)

	def _prepare_dialog(self) -> None:
		"""Map this window so the next message box stays in front of it"""
		prepare_message_parent(self)

	def _selected_sub_dir(self) -> Path | None:
		"""Resolve tree selection to a top-level destination sub directory"""
		selection = self._tree.selection()
		if not selection:
			return None
		selected_path = Path(selection[0])
		if selected_path in self._destination.sub_dir_paths:
			return selected_path
		parent_iid = self._tree.parent(selection[0])
		if not parent_iid:
			return None
		parent_path = Path(parent_iid)
		if parent_path in self._destination.sub_dir_paths:
			return parent_path
		return None

	def _create(self) -> None:
		"""Write meta and trigger files"""
		selected_path = self._selected_sub_dir()
		if selected_path is None:
			self._prepare_dialog()
			showerror(parent=self, title=self._labels.error, message=self._labels.select_todo_dir)
			return
		todo = self._todo.get()
		if todo not in self._destination.todos or not self._destination.todos[todo].get("do_something"):
			self._prepare_dialog()
			showerror(parent=self, title=self._labels.error, message=self._labels.todo_dialog_select)
			return
		self._root.create_todo(selected_path, todo)
