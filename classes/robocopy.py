#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from subprocess import Popen, PIPE, STDOUT, STARTUPINFO, STARTF_USESHOWWINDOW

class RoboCopy:
	'''Wrapper for RoboCopy'''

	def __init__(self):
		'''Create robocopy process'''
		self._startupinfo = STARTUPINFO()
		self._startupinfo.dwFlags |= STARTF_USESHOWWINDOW
		self._copy_args = ['/fp', '/ns', '/njh', '/njs', '/nc', '/a-:R']
		try:
			for line in self._yield(['/?']):
				if line.lstrip().lower().startswith('/unicode'):
					self._copy_args.append('/unicode')
				elif line.lower().startswith('/compress'):
					self._copy_args.append('/compress')
		except Exception as ex:
			raise RuntimeError(f'Unable to execute "robocopy /?":\n{ex}')

	def _popen(self, args):
		'''Use Popen to run RoboCopy'''
		self._cmd = ['robocopy'] + args
		return Popen(self._cmd,
			stdout = PIPE,
			stderr = STDOUT,
			encoding = 'utf-8',
			errors = 'ignore',
			universal_newlines = True,
			startupinfo = self._startupinfo
		)

	def _yield(self, args):
		'''Execute RoboCopy and yield output'''
		proc = self._popen(args)
		for line in proc.stdout:
			if stripped := line.strip():
				yield stripped
		self.returncode = proc.wait()

	def copy_dir(self, src, dst):
		'''Copy recursivly a directory'''
		return self._yield([src, dst] + ['/e'] + self._copy_args)

	def mirror_dir(self, src, dst):
		'''Empty destination directory and copy source into it'''
		return self._yield([src, dst] + ['/mir'] + self._copy_args)

	def copy_files(self, src, dst, filenames):
		'''Copy files into destination directory'''
		return self._yield([src, dst] + filenames + self._copy_args)

	def __repr__(self):
		'''Return command line as string'''
		return ' '.join(f'{item}' for item in self._cmd)
