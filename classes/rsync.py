#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import run, Popen, PIPE, STDOUT

class Rsync:
	'''Wrapper for rsync'''

	def __init__(self, labels=None):
		'''Create rsync process'''
		try:
			run(['rsync', '--version'])
		except:
			raise RuntimeError('Unable to execute "rsync"')
		self._labels = labels
		self._cmd = ['rsync', '-a', '-v']
		self._proc = None
		self._returncode = None
		self.lists_hashes = False

	def _popen(self, args):
		'''Use Popen to run rsync'''
		return Popen(self._cmd + args, stdout = PIPE, stderr = STDOUT, text = True)

	def _yield(self, args):
		'''Execute rsync and yield output'''
		self._returncode = None
		self._proc = self._popen(args)
		for line in self._proc.stdout:
			if stripped := line.strip():
				yield stripped, '\n'
		self._returncode = self._proc.wait()
		self._proc = None

	def terminate(self):
		'''Terminate/abort Robocopy process'''
		self._proc.terminate()
		self._proc = None

	def copy_dir(self, src, dst):
		'''Copy recursivly a directory'''
		return self._yield([f'{src}/', f'{dst}/'])

	def mirror_dir(self, src, dst):
		'''Empty destination directory and copy source into it'''
		return self._yield([f'{src}/', f'{dst}/', '--delete'])

	def copy_files(self, src, dst, filenames):
		'''Copy files into destination directory'''
		return self._yield([src.joinpath(filename) for filename in filenames] + [f'{dst}/'])

	def __repr__(self):
		'''Return command line as string'''
		if self._returncode is None:
			return ''
		if self._labels:
			try:
				returncode = f'{self._returncode} - ' + self._labels.__dict__[f'rsync_returncode_{self._returncode}']
			except KeyError:
				returncode = f'{self._returncode}'
			return self._labels.rsync_returned.replace('#', returncode)
		else:
			return f'rsync returned {self._returncode}'

	def exception_occurred(self):
		'''Return True if an exception occurred'''
		return bool(self._returncode)