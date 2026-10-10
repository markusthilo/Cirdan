#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep
from threading import Thread, Event

class Rotator:
	"""Rotating cursor"""

	def __init__(self) -> None:
		self._index = -1

	def get(self) -> str:
		"""Return character for rotation"""
		self._index += 1
		if self._index > 3:
			self._index = 0
		return "|/-\\"[self._index]

class Cylon:
	"""(      █       )"""

	def __init__(self, width: int = 16) -> None:
		self._width = width - 3 if width > 3 else 1
		self._index = self._width // 2
		self._go_right = True

	def get(self) -> str:
		"""Return string for Cylon animation"""
		if self._go_right:
			self._index += 1
			if self._index > self._width:
				self._index = self._width - 1
				self._go_right = False
		else:
			self._index -= 1
			if self._index < 0:
				self._index = 1
				self._go_right = True
		return "(" + " " * self._index + "\u2588" + " " * (self._width - self._index) + ")"

class IndicatorThread(Thread):
	"""Thread that shows an indicator while the work is running"""

	def __init__(self, message="#1 #2", indicator="rotator", echo=print, sleep=.25):
		"""Pass all attributes from GUI to work thread"""
		self._message = message
		self._indicator = Cylon() if indicator == "cylon" else Rotator()
		self._echo = echo
		self._sleep = sleep
		self._kill_event = Event()
		self._percentage = 0
		super().__init__()

	def run(self):
		"""Run thread"""
		while not self._kill_event.is_set():
			self._echo(self._message.replace("%", f"{self._percentage}").replace("#", self._indicator.get()), end="\r")
			sleep(self._sleep)

	def set_percentage(self, percentage):
		"""Set the percentage"""
		self._percentage = percentage

	def kill(self):
		"""Kill thread"""
		self._kill_event.set()