#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep

class Rotator:
	'''Rotating cursor'''

	def __init__(self, echo=print, sleep=.25):
		'''Initialize the rotation cursor'''
		self._echo = echo
		self._index = 0
		self._sleep = sleep

	def inc(self):
		'''Increment the index'''
		self._echo(f'{"|/-\\"[self._index]}  ', end='\r')
		self._index += 1
		if self._index > 3:
			self._index = 0
		if self._sleep:
			sleep(self._sleep)

class Cylon:
	'''(      █       )'''

	def __init__(self, echo=print, width=16, sleep=.25):
		'''Initialize the Cylon animation'''
		self._echo = echo
		self._width = width - 3
		if self._width < 2:
			self._width = 1
		self._index = self._width // 2
		self._sleep = sleep
		self._go_right = True

	def inc(self):
		'''Increment the index'''
		self._echo('(' + ' ' * self._index + '\u2588' + ' ' * (self._width - self._index) + ')', end='\r')

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
		if self._sleep:
			sleep(self._sleep)

