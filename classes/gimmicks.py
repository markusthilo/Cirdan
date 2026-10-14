#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep
from threading import Thread, Event
from collections.abc import Callable

class Rotator:
	"""Rotating cursor"""

	_FRAMES = "|/-\\"

	def __init__(self) -> None:
		self._index = -1

	def get(self) -> str:
		"""Return character for rotation"""
		self._index = (self._index + 1) % len(self._FRAMES)
		return self._FRAMES[self._index]

class Cylon:
	"""(      █       )"""

	def __init__(self, width: int = 16) -> None:
		self._width = max(width - 3, 1)
		self._index = self._width // 2
		self._go_right = True

	def get(self) -> str:
		"""Return string for Cylon animation"""
		if self._go_right:
			self._index += 1
			if self._index > self._width:
				self._index = self._width
				self._go_right = False
		else:
			self._index -= 1
			if self._index < 0:
				self._index = 0
				self._go_right = True
		return "(" + " " * self._index + "\u2588" + " " * (self._width - self._index) + ")"

class IndicatorThread(Thread):
	"""Thread that shows an indicator while the work is running"""

	def __init__(
		self,
		message: str | None = "% #",
		indicator: str = "rotator",
		echo: Callable[..., None] = print,
		interval: float = 0.25,
	) -> None:
		"""Start a spinner / progress indicator that calls echo"""
		self._message = message
		self._indicator = Cylon() if indicator == "cylon" else Rotator()
		self._echo = echo
		self._interval = interval
		self._kill_event = Event()
		self._percentage = "0%"
		super().__init__(daemon=True)

	def run(self) -> None:
		"""Run thread"""
		while not self._kill_event.is_set():
			frame = self._indicator.get()
			if self._message:
				text = self._message.replace("%", self._percentage, 1).replace("#", frame, 1)
			else:
				text = frame
			self._echo(text, end="\r")
			sleep(self._interval)

	def set_percentage(self, percentage: int | float | str) -> None:
		"""Set the percentage (int/float or string, with or without a trailing %)"""
		if isinstance(percentage, str):
			text = percentage.strip()
			self._percentage = text if text.endswith("%") else f"{text}%"
		else:
			self._percentage = f"{int(percentage)}%"

	def kill(self) -> None:
		"""Ask the indicator thread to stop"""
		self._kill_event.set()
