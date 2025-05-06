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
		self._copy_args = ['/e', '/fp', '/ns', '/njh', '/njs', '/nc']
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

	def _run(self, args):
		'''Run RoboCopy and return process when finished'''
		proc = self._popen(args)
		self.returncode = proc.wait()
		return proc

	def copy_dir(self, src, dst):
		'''Copy recursivly a directory'''
		return self._yield([src, dst] + self._copy_args)

	def copy_file(self, src, dst):
		'''Copy one file into destination directory'''
		proc = self._run([src.parent, dst, src.name])
		self.returncode = proc.wait()
		return proc

	def __repr__(self):
		'''Return command line as string'''
		return ' '.join(f'{item}' for item in self._cmd)
