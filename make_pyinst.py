#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import remove
from os.path import exists
from shutil import move, rmtree
import PyInstaller.__main__
from cirdan import __version__

if __name__ == '__main__':	# start here
	print('Launching PyInstaller...')
	#if exists('build'):
	#	rmtree('build')
	#if exists('dist'):
	#	rmtree('dist')
	#if exists('cirdan.dist'):
	#	rmtree('cirdan.dist')
	#if exists('download_app.dist'):
	#	rmtree('download_app.dist')
	PyInstaller.__main__.run([
		'--onedir',
        '--windowed',
		'--icon', 'appicon.ico',
		'--distpath', './',
		'--noconfirm',
		'cirdan.py'
	])
	#PyInstaller.__main__.run([
	#	'--onedir',
	#	'--noconfirm',
	#	'download_app.py'
	#])
	#move('dist/cirdan', 'cirdan.dist')
	#move('dist/download_app', 'download_app.dist')
	#rmtree('build')
	#remove('cirdan.spec')
	#remove('download_app.spec')
	with open('version.txt', 'w') as f:
		print(__version__, file=f)
	remove('cirdan.spec')
	print('Done!')