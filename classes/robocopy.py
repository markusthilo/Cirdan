#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, STDOUT, STARTUPINFO, STARTF_USESHOWWINDOW

class RoboCopy:
	'''Wrapper for RoboCopy'''

	def __init__(self, labels=None):
		'''Create robocopy process'''
		self._labels = labels
		self._startupinfo = STARTUPINFO()
		self._startupinfo.dwFlags |= STARTF_USESHOWWINDOW
		self._copy_args = ['/fp', '/ns', '/njh', '/njs', '/nc', '/a-:R']
		self._proc = None
		self._returncode = None
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
		self._returncode = None
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
		self._proc = self._popen(args)
		for line in self._proc.stdout:
			if stripped := line.strip():
				if line.endswith('%'):
					yield stripped, '\r'
				else:
					yield stripped, '\n'
		self._returncode = self._proc.wait()
		self._proc = None

	def terminate(self):
		'''Terminate/abort Robocopy process'''
		self._proc.terminate()
		self._proc = None

	def copy_dir(self, src, dst):
		'''Copy recursivly a directory'''
		return self._yield([f'{src}', f'{dst}'] + ['/e'] + self._copy_args)

	def mirror_dir(self, src, dst):
		'''Empty destination directory and copy source into it'''
		return self._yield([src, dst] + ['/mir'] + self._copy_args)

	def copy_files(self, src, dst, filenames):
		'''Copy files into destination directory'''
		return self._yield([src, dst] + filenames + self._copy_args)

	def __repr__(self):
		'''Return command line as string'''
		if self._returncode is None:
			return ''
		if self._labels:
			try:
				returncode = f'{self._returncode} - ' + self._labels.__dict__[f'robocopy_returncode_{self._returncode}']
			except KeyError:
				returncode = f'{self._returncode}'
			return self._labels.robocopy_returned.replace('#', returncode)
		else:
			return f'Robocopy returned {self._returncode}'

	def exception_occurred(self):
		'''Return True if an exception occurred'''
		if self._returncode is None:
			return False
		return self.returncode > 5
