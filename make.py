#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import remove
from os.path import exists
from shutil import move, rmtree
import PyInstaller.__main__
from cirdan import __version__

if __name__ == '__main__':	# start here
	print('Removing existing executables')
	if exists('cirdan.exe'):
		remove('cirdan.exe')
	if exists('downloader.exe'):
		remove('downloader.exe')
	print('Launching PyInstaller')
	PyInstaller.__main__.run(['--noconfirm', 'make.spec'])
	move('dist/cirdan.exe', './')
	move('dist/downloader.exe', './')
	print('Cleaning up')
	if exists('build'):
		rmtree('build')
	if exists('dist'):
		rmtree('dist')
	if exists('__pycache__'):
		rmtree('__pycache__')
	if exists('classes/__pycache__'):
		rmtree('classes/__pycache__')
	with open('version.txt', 'w') as f:
		print(__version__, file=f)
	print('Done!')