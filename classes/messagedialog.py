#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import Misc, TclError

def prepare_message_parent(parent: Misc) -> None:
	"""Map parent, then keep the next tk message box above it"""
	top = parent.winfo_toplevel()
	try:
		top.deiconify()
		top.update()
	except TclError:
		return

	pending: dict[str, str | None] = {"id": None}

	def stop(_event: object = None) -> None:
		after_id = pending["id"]
		pending["id"] = None
		if after_id is not None:
			try:
				top.after_cancel(after_id)
			except TclError:
				pass

	def raise_box(tries: int = 10) -> None:
		pending["id"] = None
		path = str(top)
		name = ".__tk__messagebox" if path == "." else f"{path}.__tk__messagebox"
		try:
			if not top.winfo_exists() or not int(top.tk.call("winfo", "exists", name)):
				if tries > 0 and top.winfo_exists():
					pending["id"] = top.after(20, raise_box, tries - 1)
				return
			top.tk.call("wm", "attributes", name, "-topmost", 1)
			top.tk.call("wm", "lift", name, path)
			top.tk.call("focus", "-force", name)
		except TclError:
			return

	top.bind("<Destroy>", stop, add="+")
	pending["id"] = top.after(1, raise_box)
